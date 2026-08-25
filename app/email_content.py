from __future__ import annotations

from typing import Final

from jinja2 import DictLoader, Environment, select_autoescape

EMAIL_SUBJECT_TEMPLATE_DEFAULT: Final = "Feliz cumpleaños, {{name}}! 🎉"

####################### THE ONE CURRENLTY USING ####################
######################## TO Modify From Name and Subject template go to .env ###############
EMAIL_HTML_TEMPLATE: Final = """<!DOCTYPE html>
<html lang="es">
  <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.5; color: #1e293b; max-width: 540px; margin: 0 auto; padding: 24px 16px; background-color: #ffffff;">
    <p style="font-size: 16px; margin: 0 0 16px 0;">{{ salutation }} <strong>{{ name }}</strong>,</p>

    {% if image_mode == "local" %}
    <div style="text-align: center; margin: 20px 0;">
      <img src="cid:{{ inline_image_content_id }}" alt="{{ image_alt }}" width="{{ image_width }}" style="max-width: 100%; height: auto; border-radius: 12px; display: block; margin: 0 auto;">
    </div>
    {% elif image_mode == "url" %}
    <div style="text-align: center; margin: 20px 0;">
      <img src="{{ image_url }}" alt="{{ image_alt }}" width="{{ image_width }}" style="max-width: 100%; height: auto; border-radius: 12px; display: block; margin: 0 auto;">
    </div>
    {% endif %}

    <p style="font-size: 14px; color: #64748b; text-align: center; margin: 20px 0 0 0;">
      {{ signature_intro }}<br>
      <strong style="color: #0f172a;">{{ from_name }}</strong>
    </p>
  </body>
</html>
"""

EMAIL_TEXT_TEMPLATE: Final = """Feliz cumpleaños, {{ name }}! 🎉

Hi {{ name }},

{% if image_mode == "url" %}{{ image_url }}

{% endif %}Wishing you a wonderful birthday filled with joy, laughter, and a year ahead full of great moments.

{{ signature_closing }},
{{ from_name }}
"""

DEFAULT_SALUTATION: Final = "Estimado/a"
FEMALE_SALUTATION: Final = "Estimada"
MALE_SALUTATION: Final = "Estimado"
SIGNATURE_INTRO: Final = "Un cordial saludo,"
SIGNATURE_CLOSING: Final = "Best wishes"

DEFAULT_BIRTHDAY_IMAGE_MODE: Final = "local"
DEFAULT_BIRTHDAY_IMAGE_PATH: Final = "app/assets/birthday_banner.jpg"
DEFAULT_BIRTHDAY_IMAGE_URL: Final = ""
DEFAULT_BIRTHDAY_IMAGE_ALT: Final = "Happy Birthday"
DEFAULT_BIRTHDAY_IMAGE_WIDTH: Final = 600
INLINE_IMAGE_CONTENT_ID: Final = "birthday_banner"


def build_email_template_environment() -> Environment:
    return Environment(
        loader=DictLoader(
            {
                "birthday_email.html": EMAIL_HTML_TEMPLATE,
                "birthday_email.txt": EMAIL_TEXT_TEMPLATE,
            }
        ),
        autoescape=select_autoescape(["html", "xml"]),
    )
