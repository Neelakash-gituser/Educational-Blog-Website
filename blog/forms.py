from django import forms
from django.utils.text import slugify

from .models import Comment, ContactMessage, Post, Subscriber, Tag


class PostForm(forms.ModelForm):
    """The editor used in the dashboard. Tags are entered as free text."""

    tags_text = forms.CharField(
        label="Tags",
        required=False,
        help_text="Comma separated, e.g. recursion, big-o, python",
        widget=forms.TextInput(attrs={"placeholder": "recursion, big-o, python"}),
    )

    class Meta:
        model = Post
        fields = (
            "title",
            "subtitle",
            "category",
            "excerpt",
            "content",
            "cover_image",
            "cover_caption",
            "status",
            "allow_comments",
        )
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "How Fourier transforms actually work"}),
            "subtitle": forms.TextInput(
                attrs={"placeholder": "A short standfirst that sets up the piece (optional)"}
            ),
            "excerpt": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Leave blank to generate from the body."}
            ),
            "content": forms.Textarea(
                attrs={
                    "rows": 24,
                    "class": "markdown-editor",
                    "spellcheck": "true",
                    "placeholder": "Write in Markdown. Fence code blocks with ``` and a language name.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_text"].initial = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )
        self.fields["category"].empty_label = "— pick a topic —"

    def clean_tags_text(self):
        raw = self.cleaned_data.get("tags_text", "")
        names, seen = [], set()
        for chunk in raw.replace("\n", ",").split(","):
            name = " ".join(chunk.split())[:50]
            if name and slugify(name) and slugify(name) not in seen:
                seen.add(slugify(name))
                names.append(name)
        if len(names) > 8:
            raise forms.ValidationError("Eight tags is plenty — pick the best ones.")
        return names

    def save(self, commit=True):
        post = super().save(commit=commit)
        if commit:
            self.save_tags(post)
        return post

    def save_tags(self, post):
        tags = []
        for name in self.cleaned_data.get("tags_text", []):
            tag = Tag.objects.filter(slug=slugify(name)).first()
            if tag is None:
                tag = Tag.objects.create(name=name, slug=slugify(name))
            tags.append(tag)
        post.tags.set(tags)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Add to the discussion. Markdown and ``` code blocks work here.",
                }
            )
        }
        labels = {"body": ""}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError("That is a little too short to be useful.")
        return body


class ContactForm(forms.ModelForm):
    # Bots fill in every field they find; humans never see this one.
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
            "subject": forms.TextInput(attrs={"placeholder": "What is this about?"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "Your message…"}),
        }

    def clean_honeypot(self):
        if self.cleaned_data.get("honeypot"):
            raise forms.ValidationError("Spam detected.")
        return ""


class SubscribeForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(
                attrs={"placeholder": "you@example.com", "aria-label": "Email address"}
            )
        }
        labels = {"email": ""}

    def clean_email(self):
        return self.cleaned_data["email"].lower()
