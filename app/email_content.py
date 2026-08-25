from __future__ import annotations

from typing import Final

from jinja2 import DictLoader, Environment, select_autoescape

# ¡Feliz cumpleaños, {{ name ~ ' ' ~ last_name }}! 🎉
# "Feliz cumpleaños, {{ display_name }}! 🎉"
EMAIL_SUBJECT_TEMPLATE_DEFAULT: Final = "Feliz cumpleaños, {{ display_name }}! 🎉"
BP_REMINDER_TO_ADDRESS_DEFAULT: Final = "elias.arellano@americansmartbusiness.com"
BP_REMINDER_TO_NAME_DEFAULT: Final = "Jorge Arellano"
BP_REMINDER_SUBJECT_TEMPLATE: Final = (
    "Recordatorio BP: llamada de cumpleaños para {{ display_name }}"
)

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

BP_REMINDER_HTML_TEMPLATE: Final = """<!DOCTYPE html>
<html lang="es">
  <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.5; color: #1e293b; max-width: 540px; margin: 0 auto; padding: 24px 16px; background-color: #ffffff;">
    <p style="font-size: 16px; margin: 0 0 16px 0;">Se detectó un cliente BP en el flujo de cumpleaños.</p>
    <ul style="padding-left: 20px; margin: 0 0 16px 0;">
      <li><strong>Nombre completo:</strong> {{ display_name }}</li>
      <li><strong>Fecha de cumpleaños:</strong> {{ birthday_date }}</li>
      <li><strong>Móvil:</strong> {{ mobile_phone }}</li>
      <li><strong>Estatus:</strong> {{ bp_status }}</li>
    </ul>
    <p style="font-size: 14px; color: #64748b; margin: 0;">{{ bp_follow_up_text }}</p>
  </body>
</html>
"""

BP_REMINDER_TEXT_TEMPLATE: Final = """Cliente BP detectado en el flujo de cumpleaños.

Nombre completo: {{ display_name }}
Fecha de cumpleaños: {{ birthday_date }}
Móvil: {{ mobile_phone }}
Estatus: {{ bp_status }}

{{ bp_follow_up_text }}
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
BP_STATUS_LABEL: Final = "BP override activo"
BP_FOLLOW_UP_TEXT: Final = "No se envió correo al cliente. Favor de realizar llamada de felicitación."


def build_email_template_environment() -> Environment:
    return Environment(
        loader=DictLoader(
            {
                "birthday_email.html": EMAIL_HTML_TEMPLATE,
                "birthday_email.txt": EMAIL_TEXT_TEMPLATE,
                "bp_call_reminder.html": BP_REMINDER_HTML_TEMPLATE,
                "bp_call_reminder.txt": BP_REMINDER_TEXT_TEMPLATE,
            }
        ),
        autoescape=select_autoescape(["html", "xml"]),
    )

