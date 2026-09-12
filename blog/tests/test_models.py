from django.test import TestCase
from django.utils import timezone

from blog.models import Comment, Post, unique_slugify

from .factories import make_category, make_post, make_user


class SlugTests(TestCase):
    def setUp(self):
        self.author = make_user("author", writer=True)

    def test_slug_is_derived_from_title(self):
        post = make_post(self.author, title="Binary Search Is Hard")
        self.assertEqual(post.slug, "binary-search-is-hard")

    def test_duplicate_titles_get_distinct_slugs(self):
        first = make_post(self.author, title="Same Title")
        second = make_post(self.author, title="Same Title")
        self.assertEqual(first.slug, "same-title")
        self.assertEqual(second.slug, "same-title-2")

    def test_slug_survives_a_title_with_no_slug_characters(self):
        post = make_post(self.author, title="!!!")
        self.assertEqual(post.slug, "untitled")

    def test_unique_slugify_ignores_the_instance_itself(self):
        post = make_post(self.author, title="Keep Me")
        self.assertEqual(unique_slugify(post, "Keep Me"), "keep-me")


class PostBehaviourTests(TestCase):
    def setUp(self):
        self.author = make_user("author", writer=True)

    def test_publishing_sets_published_at(self):
        post = make_post(self.author)
        self.assertIsNotNone(post.published_at)
        self.assertTrue(post.is_published)

    def test_draft_has_no_publish_date_and_is_not_published(self):
        post = make_post(self.author, published=False)
        self.assertIsNone(post.published_at)
        self.assertFalse(post.is_published)

    def test_future_dated_post_is_not_published_yet(self):
        post = make_post(self.author)
        post.published_at = timezone.now() + timezone.timedelta(days=2)
        post.save()
        self.assertFalse(post.is_published)
        self.assertNotIn(post, Post.objects.published())

    def test_body_is_rendered_and_measured_on_save(self):
        post = make_post(self.author, content="# Title\n\n" + "word " * 440)
        self.assertIn("<h1", post.content_html)
        self.assertEqual(post.read_minutes, 2)
        self.assertGreater(post.words, 400)

    def test_excerpt_is_generated_when_left_blank(self):
        post = make_post(self.author, content="## Heading\n\nPlain sentence of prose.")
        self.assertIn("Plain sentence", post.excerpt)
        self.assertNotIn("##", post.excerpt)

    def test_explicit_excerpt_is_kept(self):
        post = make_post(self.author, excerpt="Mine.", content="Something else entirely.")
        self.assertEqual(post.excerpt, "Mine.")

    def test_table_of_contents_needs_more_than_one_heading(self):
        single = make_post(self.author, title="One", content="## Only heading\n\ntext")
        several = make_post(
            self.author, title="Many", content="## A\n\ntext\n\n## B\n\ntext\n\n## C\n\ntext"
        )
        self.assertEqual(single.toc_html, "")
        self.assertIn("#b", several.toc_html)

    def test_register_view_increments_without_touching_updated_at(self):
        post = make_post(self.author)
        before = post.updated_at
        post.register_view()
        post.refresh_from_db()
        self.assertEqual(post.view_count, 1)
        self.assertEqual(post.updated_at, before)

    def test_related_posts_prefer_shared_tags(self):
        from blog.models import Tag

        tag = Tag.objects.create(name="algorithms")
        other = make_category("Physics")
        subject = make_post(self.author, title="Subject")
        subject.tags.add(tag)
        tagged = make_post(self.author, title="Tagged too")
        tagged.tags.add(tag)
        unrelated = make_post(self.author, title="Unrelated", category=other)

        related = list(subject.related_posts())
        self.assertIn(tagged, related)
        self.assertNotIn(unrelated, related)
        self.assertNotIn(subject, related)


class CommentTests(TestCase):
    def setUp(self):
        self.author = make_user("author", writer=True)
        self.reader = make_user("reader")
        self.post = make_post(self.author)

    def test_body_is_rendered_on_save(self):
        comment = Comment.objects.create(post=self.post, author=self.reader, body="**bold**")
        self.assertIn("<strong>bold</strong>", comment.body_html)

    def test_threading_is_flattened_to_one_level(self):
        root = Comment.objects.create(post=self.post, author=self.reader, body="root")
        reply = Comment.objects.create(post=self.post, author=self.reader, body="reply", parent=root)
        deep = Comment.objects.create(post=self.post, author=self.reader, body="deep", parent=reply)
        self.assertEqual(deep.parent, root)

    def test_comment_count_ignores_unapproved(self):
        Comment.objects.create(post=self.post, author=self.reader, body="visible")
        Comment.objects.create(post=self.post, author=self.reader, body="hidden", is_approved=False)
        self.assertEqual(self.post.comment_count(), 1)


class QuerySetTests(TestCase):
    def setUp(self):
        self.author = make_user("author", writer=True)
        self.category = make_category("Physics")
        self.published = make_post(
            self.author, title="Spinning tops", category=self.category, content="angular momentum"
        )
        self.draft = make_post(self.author, title="Half written", published=False)

    def test_published_excludes_drafts(self):
        self.assertEqual(list(Post.objects.published()), [self.published])

    def test_drafts_excludes_published(self):
        self.assertEqual(list(Post.objects.drafts()), [self.draft])

    def test_search_matches_title_body_and_category(self):
        self.assertIn(self.published, Post.objects.published().search("spinning"))
        self.assertIn(self.published, Post.objects.published().search("angular"))
        self.assertIn(self.published, Post.objects.published().search("physics"))
        self.assertNotIn(self.published, Post.objects.published().search("thermodynamics"))

    def test_with_counts_annotates_comments_and_likes(self):
        reader = make_user("reader")
        self.published.likes.add(reader)
        from blog.models import Comment

        Comment.objects.create(post=self.published, author=reader, body="hi")
        annotated = Post.objects.published().with_counts().get(pk=self.published.pk)
        self.assertEqual(annotated.comment_total, 1)
        self.assertEqual(annotated.like_total, 1)
