from django.test import SimpleTestCase

from blog.markdown_utils import (
    reading_time,
    render_comment,
    render_markdown,
    render_toc,
    strip_markdown,
    word_count,
)


class RenderingTests(SimpleTestCase):
    def test_fenced_code_is_highlighted(self):
        html = render_markdown("```python\ndef f():\n    return 1\n```")
        self.assertIn("codehilite", html)
        self.assertIn('class="k"', html)  # keyword token from Pygments

    def test_language_class_is_preserved_for_the_label(self):
        html = render_markdown("```python\nx = 1\n```")
        self.assertIn("language-python", html)

    def test_tables_footnotes_and_admonitions_render(self):
        html = render_markdown(
            "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
            "Text[^1]\n\n[^1]: A footnote.\n\n"
            "!!! note\n    Boxed out.\n"
        )
        self.assertIn("<table>", html)
        self.assertIn("footnote", html)
        self.assertIn("admonition", html)

    def test_maths_is_left_for_mathjax(self):
        html = render_markdown(r"Inline \(x^2\) and $$E = mc^2$$")
        self.assertIn("arithmatex", html)
        self.assertIn("x^2", html)

    def test_headings_get_ids_for_the_table_of_contents(self):
        html = render_markdown("## Section one\n\ntext")
        self.assertIn('id="section-one"', html)

    def test_html_inside_a_code_fence_is_escaped_exactly_once(self):
        html = render_markdown("```html\n<b>bold</b>\n```")
        self.assertIn("&lt;", html)
        self.assertNotIn("&amp;lt;", html)

    def test_bare_urls_become_links(self):
        self.assertIn('href="https://example.com"', render_markdown("See https://example.com"))

    def test_toc_lists_every_heading(self):
        toc = render_toc("## First\n\ntext\n\n## Second\n\ntext")
        self.assertIn("#first", toc)
        self.assertIn("#second", toc)


class SanitisingTests(SimpleTestCase):
    def test_script_tags_are_stripped_from_posts(self):
        html = render_markdown("Hello\n\n<script>alert('xss')</script>")
        self.assertNotIn("<script", html)
        self.assertNotIn("alert(", html)

    def test_script_bodies_are_removed_not_left_as_text(self):
        html = render_markdown("Hi\n\n<script>steal()</script>")
        self.assertNotIn("steal()", html)

    def test_event_handlers_and_inline_styles_are_stripped(self):
        html = render_markdown('<div onclick="steal()" style="position:fixed">hi</div>')
        self.assertNotIn("onclick", html)
        self.assertNotIn("style=", html)

    def test_javascript_urls_are_stripped(self):
        html = render_markdown('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", html)

    def test_iframes_are_not_allowed(self):
        html = render_markdown('<iframe src="https://evil.example"></iframe>')
        self.assertNotIn("<iframe", html)

    def test_comments_allow_formatting_but_not_images_or_scripts(self):
        html = render_comment("**bold** <script>x()</script> ![img](https://e/x.png)")
        self.assertIn("<strong>bold</strong>", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("<img", html)

    def test_comments_keep_code_blocks(self):
        html = render_comment("```python\nprint(1)\n```")
        self.assertIn("codehilite", html)


class MeasurementTests(SimpleTestCase):
    def test_strip_markdown_removes_syntax(self):
        self.assertEqual(strip_markdown("## Hi *there*"), "Hi there")

    def test_strip_markdown_truncates_on_a_word_boundary(self):
        text = strip_markdown("one two three four five six seven", limit=12)
        self.assertTrue(text.endswith("…"))
        self.assertLessEqual(len(text), 14)

    def test_word_count_ignores_markup(self):
        self.assertEqual(word_count("**one** two `three`"), 3)

    def test_reading_time_is_never_zero(self):
        self.assertEqual(reading_time("tiny"), 1)
        self.assertEqual(reading_time("word " * 660), 3)
