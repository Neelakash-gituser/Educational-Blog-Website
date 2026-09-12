from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from blog.models import Comment, ContactMessage, Post, Subscriber, Tag

from .factories import make_category, make_post, make_user


class ReadingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = make_user("author", writer=True)
        cls.category = make_category("Physics", color="#0ea5e9", icon="⚛")
        cls.post = make_post(
            cls.author,
            title="Spinning tops",
            category=cls.category,
            content="## Angular momentum\n\nA body of text about torque.",
        )
        cls.tag = Tag.objects.create(name="mechanics")
        cls.post.tags.add(cls.tag)
        cls.draft = make_post(cls.author, title="Not ready", published=False)

    def test_home_lists_published_posts_only(self):
        response = self.client.get(reverse("blog:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spinning tops")
        self.assertNotContains(response, "Not ready")

    def test_home_renders_for_an_empty_site(self):
        Post.objects.all().delete()
        response = self.client.get(reverse("blog:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No posts published yet")

    def test_post_detail_renders_body_html(self):
        response = self.client.get(self.post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Angular momentum")
        self.assertContains(response, 'id="angular-momentum"')

    def test_draft_is_hidden_from_the_public(self):
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)

    def test_draft_is_visible_to_its_author(self):
        self.client.force_login(self.author)
        response = self.client.get(self.draft.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is a draft")

    def test_draft_is_visible_to_staff(self):
        self.client.force_login(make_user("mod", staff=True))
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 200)

    def test_view_counter_increments_once_per_session(self):
        self.client.get(self.post.get_absolute_url())
        self.client.get(self.post.get_absolute_url())
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 1)

    def test_author_does_not_inflate_their_own_view_count(self):
        self.client.force_login(self.author)
        self.client.get(self.post.get_absolute_url())
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 0)

    def test_listing_search_and_sort(self):
        url = reverse("blog:post_list")
        self.assertContains(self.client.get(url, {"q": "spinning"}), "Spinning tops")
        self.assertNotContains(self.client.get(url, {"q": "chemistry"}), "Spinning tops")
        for sort in ("recent", "popular", "discussed", "liked", "nonsense"):
            self.assertEqual(self.client.get(url, {"sort": sort}).status_code, 200)

    def test_category_tag_and_author_pages(self):
        for url in (
            self.category.get_absolute_url(),
            self.tag.get_absolute_url(),
            reverse("blog:author", args=[self.author.username]),
            reverse("blog:search") + "?q=torque",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Spinning tops")

    def test_topics_page_lists_topics_with_counts(self):
        response = self.client.get(reverse("blog:topics"))
        self.assertContains(response, "Physics")
        self.assertContains(response, "1 article")
        self.assertContains(response, "#mechanics")

    def test_static_pages(self):
        for name in ("blog:about", "blog:contact"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_feed_and_sitemap(self):
        feed = self.client.get(reverse("post_feed"))
        self.assertEqual(feed.status_code, 200)
        self.assertIn("Spinning tops", feed.content.decode())
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn(self.post.get_absolute_url(), sitemap.content.decode())

    def test_unknown_url_returns_404(self):
        self.assertEqual(self.client.get("/no-such-article/").status_code, 404)

    def test_reserved_paths_are_not_shadowed_by_post_slugs(self):
        """A post slugged "about" must not take over the about page."""
        make_post(self.author, title="About", content="body")
        response = self.client.get(reverse("blog:about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Why this blog exists")


class CommentTests(TestCase):
    def setUp(self):
        self.author = make_user("author", writer=True)
        self.reader = make_user("reader")
        self.post = make_post(self.author, title="Discussed post")

    def url(self):
        return reverse("blog:comment_create", args=[self.post.slug])

    def test_anonymous_visitor_is_sent_to_login(self):
        response = self.client.post(self.url(), {"body": "hello"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertEqual(Comment.objects.count(), 0)

    def test_signed_in_reader_can_comment(self):
        self.client.force_login(self.reader)
        response = self.client.post(self.url(), {"body": "Great **post**"}, follow=True)
        self.assertEqual(response.status_code, 200)
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.reader)
        self.assertTrue(comment.is_approved)
        self.assertContains(response, "Great <strong>post</strong>", html=False)

    def test_reply_attaches_to_its_parent(self):
        root = Comment.objects.create(post=self.post, author=self.author, body="root")
        self.client.force_login(self.reader)
        self.client.post(self.url(), {"body": "a reply", "parent": root.pk})
        reply = Comment.objects.get(body="a reply")
        self.assertEqual(reply.parent, root)

    def test_empty_comment_is_rejected(self):
        self.client.force_login(self.reader)
        self.client.post(self.url(), {"body": " "})
        self.assertEqual(Comment.objects.count(), 0)

    def test_comments_can_be_closed_per_post(self):
        self.post.allow_comments = False
        self.post.save()
        self.client.force_login(self.reader)
        self.client.post(self.url(), {"body": "hello"})
        self.assertEqual(Comment.objects.count(), 0)

    @override_settings(COMMENT_MODERATION=True)
    def test_moderation_holds_comments_back(self):
        self.client.force_login(self.reader)
        self.client.post(self.url(), {"body": "needs approval"})
        comment = Comment.objects.get()
        self.assertFalse(comment.is_approved)
        self.assertNotContains(self.client.get(self.post.get_absolute_url()), "needs approval")

    def test_author_can_edit_their_own_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.reader, body="typo")
        self.client.force_login(self.reader)
        self.client.post(reverse("blog:comment_edit", args=[comment.pk]), {"body": "fixed"})
        comment.refresh_from_db()
        self.assertEqual(comment.body, "fixed")
        self.assertTrue(comment.is_edited)

    def test_other_readers_cannot_edit_or_delete_a_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.reader, body="mine")
        self.client.force_login(make_user("stranger"))
        self.assertEqual(
            self.client.post(reverse("blog:comment_edit", args=[comment.pk]), {"body": "hacked"}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(reverse("blog:comment_delete", args=[comment.pk])).status_code, 400
        )
        comment.refresh_from_db()
        self.assertEqual(comment.body, "mine")

    def test_staff_can_delete_any_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.reader, body="spam")
        self.client.force_login(make_user("mod", staff=True))
        self.client.post(reverse("blog:comment_delete", args=[comment.pk]))
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_like_toggles(self):
        comment = Comment.objects.create(post=self.post, author=self.author, body="hi")
        self.client.force_login(self.reader)
        url = reverse("blog:comment_like", args=[comment.pk])
        self.client.post(url, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(comment.likes.count(), 1)
        self.client.post(url, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(comment.likes.count(), 0)

    def test_post_author_can_moderate_comments_on_their_post(self):
        comment = Comment.objects.create(
            post=self.post, author=self.reader, body="waiting", is_approved=False
        )
        self.client.force_login(self.author)
        self.client.post(reverse("blog:comment_moderate", args=[comment.pk]), {"action": "approve"})
        comment.refresh_from_db()
        self.assertTrue(comment.is_approved)

    def test_a_stranger_cannot_moderate(self):
        comment = Comment.objects.create(post=self.post, author=self.reader, body="x", is_approved=False)
        self.client.force_login(make_user("stranger"))
        response = self.client.post(
            reverse("blog:comment_moderate", args=[comment.pk]), {"action": "approve"}
        )
        self.assertEqual(response.status_code, 400)


class ReaderActionTests(TestCase):
    def setUp(self):
        self.author = make_user("author", writer=True)
        self.reader = make_user("reader")
        self.post = make_post(self.author)

    def test_like_requires_login(self):
        response = self.client.post(reverse("blog:post_like", args=[self.post.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.post.likes.count(), 0)

    def test_like_and_unlike_return_json_for_ajax(self):
        self.client.force_login(self.reader)
        url = reverse("blog:post_like", args=[self.post.slug])
        first = self.client.post(url, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(first.json(), {"liked": True, "count": 1})
        second = self.client.post(url, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(second.json(), {"liked": False, "count": 0})

    def test_bookmark_populates_the_reading_list(self):
        self.client.force_login(self.reader)
        self.client.post(reverse("blog:post_bookmark", args=[self.post.slug]))
        response = self.client.get(reverse("blog:reading_list"))
        self.assertContains(response, self.post.title)

    def test_reading_list_requires_login(self):
        response = self.client.get(reverse("blog:reading_list"))
        self.assertEqual(response.status_code, 302)

    def test_get_is_not_allowed_for_state_changing_actions(self):
        self.client.force_login(self.reader)
        for name in ("blog:post_like", "blog:post_bookmark"):
            self.assertEqual(
                self.client.get(reverse(name, args=[self.post.slug])).status_code, 405
            )


class DashboardTests(TestCase):
    def setUp(self):
        self.writer = make_user("writer", writer=True)
        self.reader = make_user("reader")
        self.category = make_category("Computer Science")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("blog:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_readers_get_a_polite_403(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("blog:dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "author account", status_code=403)

    def test_writer_sees_only_their_own_posts(self):
        mine = make_post(self.writer, title="Mine")
        theirs = make_post(make_user("other", writer=True), title="Theirs")
        self.client.force_login(self.writer)
        response = self.client.get(reverse("blog:dashboard"))
        self.assertContains(response, mine.title)
        self.assertNotContains(response, theirs.title)

    def test_writing_a_post_creates_tags_and_publishes(self):
        self.client.force_login(self.writer)
        response = self.client.post(
            reverse("blog:post_create"),
            {
                "title": "Indexes matter",
                "subtitle": "A short standfirst",
                "category": self.category.pk,
                "excerpt": "",
                "content": "## Why\n\n```sql\nSELECT 1;\n```",
                "cover_caption": "",
                "status": Post.Status.PUBLISHED,
                "tags_text": "postgres, Performance, postgres",
                "allow_comments": "on",
            },
        )
        post = Post.objects.get(title="Indexes matter")
        self.assertRedirects(response, post.get_absolute_url())
        self.assertTrue(post.is_published)
        self.assertEqual(post.author, self.writer)
        self.assertEqual(
            sorted(post.tags.values_list("slug", flat=True)), ["performance", "postgres"]
        )
        self.assertIn("codehilite", post.content_html)
        self.assertTrue(post.excerpt)

    def test_too_many_tags_is_rejected(self):
        self.client.force_login(self.writer)
        response = self.client.post(
            reverse("blog:post_create"),
            {
                "title": "Tag soup",
                "content": "body",
                "status": Post.Status.DRAFT,
                "tags_text": ",".join(f"tag{i}" for i in range(9)),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(title="Tag soup").exists())

    def test_draft_redirects_to_the_dashboard(self):
        self.client.force_login(self.writer)
        response = self.client.post(
            reverse("blog:post_create"),
            {"title": "Draft one", "content": "body", "status": Post.Status.DRAFT, "tags_text": ""},
        )
        self.assertRedirects(response, reverse("blog:dashboard"))
        self.assertFalse(Post.objects.get(title="Draft one").is_published)

    def test_writers_cannot_edit_another_authors_post(self):
        other = make_post(make_user("other", writer=True), title="Not yours")
        self.client.force_login(self.writer)
        self.assertEqual(
            self.client.get(reverse("blog:post_edit", args=[other.slug])).status_code, 403
        )
        self.assertEqual(
            self.client.post(reverse("blog:post_delete", args=[other.slug])).status_code, 400
        )
        self.assertTrue(Post.objects.filter(pk=other.pk).exists())

    def test_editing_keeps_the_slug_and_updates_the_body(self):
        post = make_post(self.writer, title="Original title")
        self.client.force_login(self.writer)
        self.client.post(
            reverse("blog:post_edit", args=[post.slug]),
            {
                "title": "Original title",
                "content": "Rewritten body text.",
                "status": Post.Status.PUBLISHED,
                "tags_text": "",
            },
        )
        post.refresh_from_db()
        self.assertEqual(post.slug, "original-title")
        self.assertIn("Rewritten body", post.content_html)

    def test_author_can_delete_their_post(self):
        post = make_post(self.writer, title="Goodbye")
        self.client.force_login(self.writer)
        self.client.post(reverse("blog:post_delete", args=[post.slug]))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_markdown_preview_returns_rendered_html(self):
        self.client.force_login(self.writer)
        response = self.client.post(
            reverse("blog:markdown_preview"), {"content": "# Hi\n\n```python\nx = 1\n```"}
        )
        html = response.json()["html"]
        self.assertIn("<h1", html)
        self.assertIn("codehilite", html)

    def test_markdown_preview_requires_login(self):
        response = self.client.post(reverse("blog:markdown_preview"), {"content": "# Hi"})
        self.assertEqual(response.status_code, 302)

    def test_staff_may_edit_any_post(self):
        post = make_post(self.writer, title="Staff editable")
        self.client.force_login(make_user("mod", staff=True, writer=False))
        self.assertEqual(
            self.client.get(reverse("blog:post_edit", args=[post.slug])).status_code, 200
        )


class ContactAndSubscribeTests(TestCase):
    def test_contact_form_stores_the_message(self):
        response = self.client.post(
            reverse("blog:contact"),
            {
                "name": "Ada",
                "email": "ada@example.com",
                "subject": "A pitch",
                "message": "I would like to write about compilers.",
            },
        )
        self.assertRedirects(response, reverse("blog:contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_honeypot_blocks_bots(self):
        self.client.post(
            reverse("blog:contact"),
            {
                "name": "Bot",
                "email": "bot@example.com",
                "subject": "Cheap pills",
                "message": "spam",
                "honeypot": "filled in",
            },
        )
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_subscribing_is_idempotent_and_case_insensitive(self):
        url = reverse("blog:subscribe")
        self.client.post(url, {"email": "Reader@Example.com"})
        self.client.post(url, {"email": "reader@example.com"})
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_invalid_email_is_not_stored(self):
        self.client.post(reverse("blog:subscribe"), {"email": "not-an-email"})
        self.assertEqual(Subscriber.objects.count(), 0)


class AccountTests(TestCase):
    def test_signup_creates_a_profile_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "newcomer",
                "email": "newcomer@example.com",
                "display_name": "New Comer",
                "password1": "a-strong-passphrase-42",
                "password2": "a-strong-passphrase-42",
            },
        )
        self.assertRedirects(response, reverse("blog:home"))
        user = User.objects.get(username="newcomer")
        self.assertEqual(user.profile.display_name, "New Comer")
        self.assertFalse(user.profile.can_write)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_is_rejected(self):
        make_user("first")
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "second",
                "email": "first@example.com",
                "password1": "a-strong-passphrase-42",
                "password2": "a-strong-passphrase-42",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="second").exists())

    def test_login_and_logout(self):
        make_user("reader", password="a-strong-passphrase-42")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "reader", "password": "a-strong-passphrase-42"},
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_page_is_editable_by_its_owner(self):
        user = make_user("reader")
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "display_name": "Reader One",
                "headline": "Curious about optics",
                "bio": "Hello.",
                "email": "reader@example.com",
                "first_name": "Reader",
                "last_name": "One",
                "location": "",
                "website": "",
                "github": "",
                "twitter": "",
                "linkedin": "",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile_edit"))
        user.refresh_from_db()
        self.assertEqual(user.profile.display_name, "Reader One")
        self.assertEqual(user.first_name, "Reader")

    def test_profile_name_falls_back_through_display_name_then_username(self):
        user = make_user("fallback")
        self.assertEqual(user.profile.name, "fallback")
        user.first_name, user.last_name = "Grace", "Hopper"
        user.save()
        self.assertEqual(user.profile.name, "Grace Hopper")
        user.profile.display_name = "Amazing Grace"
        self.assertEqual(user.profile.name, "Amazing Grace")
        self.assertEqual(user.profile.initials, "AG")

    def test_public_author_page_is_reachable_for_a_non_writer(self):
        user = make_user("reader")
        self.assertEqual(self.client.get(user.profile.get_absolute_url()).status_code, 200)


class RedirectSafetyTests(TestCase):
    def test_subscribe_ignores_an_offsite_next(self):
        response = self.client.post(
            reverse("blog:subscribe"),
            {"email": "reader@example.com", "next": "https://evil.example/phish"},
        )
        self.assertEqual(response["Location"], reverse("blog:home"))

    def test_subscribe_honours_a_local_next(self):
        response = self.client.post(
            reverse("blog:subscribe"),
            {"email": "reader@example.com", "next": reverse("blog:post_list")},
        )
        self.assertEqual(response["Location"], reverse("blog:post_list"))


class ErrorPageTests(TestCase):
    def test_500_template_renders_without_request_context(self):
        from blog.views import server_error

        response = server_error(None)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Something broke", response.content)
