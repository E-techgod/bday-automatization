from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape


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
    assert "Estimado/a <strong>Test Person</strong>" in html_output
    assert 'src="cid:birthday_banner"' in html_output
    assert "Un cordial saludo" in html_output
    assert "Feliz cumpleaños, Test Person! 🎉" in text_output
    assert "Hi Test Person," in text_output
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
    assert "Estimado/a <strong>Test Person</strong>" in html_output
    assert image_url in html_output
    assert "cid:birthday_banner" not in html_output
    assert "Un cordial saludo" in html_output
    assert "Feliz cumpleaños, Test Person! 🎉" in text_output
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
    assert "Estimado/a <strong>Test Person</strong>" in html_output
    assert "cid:birthday_banner" not in html_output
    assert image_url not in html_output
    assert "Un cordial saludo" in html_output
    assert "Feliz cumpleaños, Test Person! 🎉" in text_output
    assert "Hi Test Person," in text_output
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
    template_env = Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = template_env.get_template(template_name)
    return template.render(
        name="Test Person",
        salutation=salutation,
        image_mode=image_mode,
        image_alt="Happy Birthday banner",
        image_width=600,
        image_url=image_url,
        from_name="Example Sender",
    )
