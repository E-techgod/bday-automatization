from __future__ import annotations

from app.email_content import (
    DEFAULT_SALUTATION,
    INLINE_IMAGE_CONTENT_ID,
    SIGNATURE_CLOSING,
    SIGNATURE_INTRO,
    build_email_template_environment,
)


def test_birthday_templates_render_local_image_mode() -> None:
    html_output = _render_template(
        "birthday_email.html",
        image_mode="local",
        image_url="https://assets.example.com/birthday-banner.jpg",
    )
    text_output = _render_template(
        "birthday_email.txt",
        image_mode="local",
        image_url="https://assets.example.com/birthday-banner.jpg",
    )

    assert 'lang="es"' in html_output
    assert f"{DEFAULT_SALUTATION} <strong>Test Person</strong>" in html_output
    assert f'src="cid:{INLINE_IMAGE_CONTENT_ID}"' in html_output
    assert SIGNATURE_INTRO in html_output
    assert text_output == _expected_text_output(image_mode="local", image_url="")
    assert "https://assets.example.com/birthday-banner.jpg" not in text_output


def test_birthday_templates_render_url_image_mode() -> None:
    image_url = "https://assets.example.com/birthday-banner.jpg"

    html_output = _render_template(
        "birthday_email.html",
        image_mode="url",
        image_url=image_url,
    )
    text_output = _render_template(
        "birthday_email.txt",
        image_mode="url",
        image_url=image_url,
    )

    assert 'lang="es"' in html_output
    assert f"{DEFAULT_SALUTATION} <strong>Test Person</strong>" in html_output
    assert image_url in html_output
    assert f"cid:{INLINE_IMAGE_CONTENT_ID}" not in html_output
    assert SIGNATURE_INTRO in html_output
    assert text_output == _expected_text_output(image_mode="url", image_url=image_url)
    assert image_url in text_output


def test_birthday_templates_render_none_image_mode() -> None:
    image_url = "https://assets.example.com/birthday-banner.jpg"

    html_output = _render_template(
        "birthday_email.html",
        image_mode="none",
        image_url=image_url,
    )
    text_output = _render_template(
        "birthday_email.txt",
        image_mode="none",
        image_url=image_url,
    )

    assert 'lang="es"' in html_output
    assert f"{DEFAULT_SALUTATION} <strong>Test Person</strong>" in html_output
    assert f"cid:{INLINE_IMAGE_CONTENT_ID}" not in html_output
    assert image_url not in html_output
    assert SIGNATURE_INTRO in html_output
    assert text_output == _expected_text_output(image_mode="none", image_url="")
    assert image_url not in text_output


def test_birthday_html_template_renders_salutation() -> None:
    html_output = _render_template(
        "birthday_email.html",
        image_mode="none",
        image_url="",
        salutation="Estimada",
    )

    assert "<p style=\"font-size: 16px; margin: 0 0 16px 0;\">Estimada <strong>Test Person</strong>,</p>" in html_output


def _render_template(
    template_name: str,
    *,
    image_mode: str,
    image_url: str,
    salutation: str = "Estimado/a",
) -> str:
    template_env = build_email_template_environment()
    template = template_env.get_template(template_name)
    return template.render(
        name="Test Person",
        salutation=salutation,
        image_mode=image_mode,
        image_alt="Happy Birthday banner",
        image_width=600,
        image_url=image_url,
        inline_image_content_id=INLINE_IMAGE_CONTENT_ID,
        signature_closing=SIGNATURE_CLOSING,
        signature_intro=SIGNATURE_INTRO,
        from_name="Example Sender",
    )


def _expected_text_output(*, image_mode: str, image_url: str) -> str:
    return _render_template(
        "birthday_email.txt",
        image_mode=image_mode,
        image_url=image_url,
    )
