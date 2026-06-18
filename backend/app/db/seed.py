"""
seed.py — Populate the font catalog on first startup.
Idempotent: checks existence before inserting.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Font, FontLicense

CAN_USE_DESKTOP = [
    {"name": "Videos", "description": "Apply fonts in titles, credits, and on-screen text."},
    {"name": "PDFs", "description": "Style reports, brochures, and digital documents."},
    {"name": "Greeting cards", "description": "Design unique, personalized cards for any occasion."},
    {"name": "Logos", "description": "Craft memorable, professional logo typography."},
    {"name": "Signage", "description": "Make clear, eye-catching signage for indoor or outdoor use."},
    {"name": "Flyers", "description": "Set readable, attractive headlines and layouts."},
    {"name": "Packaging", "description": "Enhance product packaging with stylish text."},
    {"name": "Album covers", "description": "Print custom text designs on album artwork."},
    {"name": "Posters", "description": "Bold, eye-catching poster layouts."},
    {"name": "Invitations", "description": "Create stylish, personalized invitations for events."},
    {"name": "Social posts", "description": "Enhance graphics and captions with unique fonts."},
    {"name": "Business cards", "description": "Craft professional, memorable business card designs."},
    {"name": "School projects", "description": "Make projects stand out with creative text."},
    {"name": "Wordmarks", "description": "Develop strong, recognizable brand wordmarks."},
    {"name": "Stationery", "description": "Design elegant letterheads, envelopes, and notes."},
]

CANNOT_USE_DESKTOP = [
    {"name": "E-books", "description": "Fonts cannot be embedded in digital books."},
    {"name": "Digital ads", "description": "Ads cannot use these fonts."},
    {"name": "Commercial print environments", "description": "Not for large-scale printing business."},
    {"name": "Websites", "description": "Fonts cannot be hosted online."},
    {"name": "Emails", "description": "Fonts not allowed in email templates."},
    {"name": "Apps", "description": "Cannot embed fonts inside applications."},
    {"name": "Sharing the font", "description": "Fonts cannot be distributed to others."},
    {"name": "Allowing others to use the font", "description": "License is for you only."},
    {"name": "Collaboration", "description": "Fonts cannot be shared in teams."},
    {"name": "Modifying", "description": "Fonts cannot be altered or edited."},
    {"name": "Installation on a server", "description": "Fonts cannot be installed on a server."},
    {"name": "AI training", "description": "Fonts not permitted for AI models."},
    {"name": "DAMs", "description": "Fonts cannot be hosted on DAMs as downloadable assets."},
]

CAN_USE_WEBFONT = [
    {"name": "Website typography", "description": "Embed via @font-face for headings and body text on a single domain."},
    {"name": "Landing pages", "description": "Use on marketing and product landing pages."},
    {"name": "Web applications", "description": "Style text in browser-based applications."},
    {"name": "Responsive layouts", "description": "Works across desktop, tablet, and mobile viewports."},
]

CANNOT_USE_WEBFONT = [
    {"name": "Multiple domains", "description": "A single webfont license covers one domain only."},
    {"name": "Agency sharing", "description": "Agencies may not share a single license across client sites."},
    {"name": "Logo-only use", "description": "If the font is only in a graphic/logo, use a Desktop license."},
    {"name": "App embedding", "description": "Use an App license for mobile or desktop applications."},
    {"name": "Email templates", "description": "Not permitted in HTML emails."},
    {"name": "Redistribution", "description": "Font files may not be distributed to end users."},
]

CAN_USE_APP = [
    {"name": "iOS apps", "description": "Embed the font in your Apple App Store application."},
    {"name": "Android apps", "description": "Bundle the font in your Google Play application."},
    {"name": "Windows Phone apps", "description": "Include the font in Windows Phone applications."},
    {"name": "Cross-platform apps", "description": "Use in React Native, Flutter, or similar frameworks."},
]

CANNOT_USE_APP = [
    {"name": "Desktop software", "description": "Use a Desktop license for desktop applications."},
    {"name": "Websites", "description": "Use a Webfont license for browser-based use."},
    {"name": "Redistribution", "description": "Font files may not be extracted or redistributed."},
]

CATALOG = [
    {
        "name": "Helvetica",
        "foundry": "Linotype",
        "category": "sans-serif",
        "description": (
            "Helvetica is one of the most widely used typefaces in the world. Designed in 1957 by "
            "Max Miedinger, its clean, neutral forms have made it a staple of graphic design and "
            "corporate identity."
        ),
        "licenses": [
            {
                "license_type": "desktop",
                "can_use": CAN_USE_DESKTOP,
                "cannot_use": CANNOT_USE_DESKTOP,
                "description": (
                    "A Desktop license allows you to install the font on your computer and use it in "
                    "desktop applications such as word processors, design tools, and print workflows."
                ),
            },
            {
                "license_type": "webfont",
                "can_use": CAN_USE_WEBFONT,
                "cannot_use": CANNOT_USE_WEBFONT,
                "description": (
                    "Webfonts allow you to embed the font into a webpage using the @font-face rule. "
                    "Annual license model. One license per domain."
                ),
            },
            {
                "license_type": "app",
                "can_use": CAN_USE_APP,
                "cannot_use": CANNOT_USE_APP,
                "description": (
                    "Select this license when developing an app for iOS, Android, or Windows Phone "
                    "and embedding the font file in your application code."
                ),
            },
            {
                "license_type": "edoc",
                "can_use": [
                    {"name": "eBooks", "description": "Embed in EPUB, MOBI, or PDF-based digital books."},
                    {"name": "eMagazines", "description": "Style digital magazine issues with embedded fonts."},
                    {"name": "eNewspapers", "description": "Use in digital newspaper publications."},
                ],
                "cannot_use": [
                    {"name": "Multiple publications", "description": "Each issue counts as a separate publication."},
                    {"name": "Print books", "description": "Not for physical / print-on-demand books."},
                ],
                "description": (
                    "An Electronic Doc license lets you embed the font in an electronic publication such as "
                    "an eBook, eMagazine, or eNewspaper. Priced per number of publications."
                ),
            },
            {
                "license_type": "digital_ad",
                "can_use": [
                    {"name": "HTML5 banner ads", "description": "Embed webfonts in HTML5 animated banner ads."},
                    {"name": "Programmatic ads", "description": "Use in display ads served across advertising networks."},
                    {"name": "Rich media ads", "description": "Use in interactive or expandable ad units."},
                ],
                "cannot_use": [
                    {"name": "Websites", "description": "Use a Webfont license for website usage."},
                    {"name": "Unlimited impressions", "description": "Impressions must be tracked; true-up required."},
                ],
                "description": (
                    "Use this license to embed fonts in digital ads such as HTML5 banners. "
                    "Priced per impression tier."
                ),
            },
        ],
    },
    {
        "name": "Garamond",
        "foundry": "Adobe",
        "category": "serif",
        "description": (
            "Garamond is a classic old-style serif typeface named after 16th century French punch-cutter "
            "Claude Garamond. Known for elegance and legibility, widely used in book and editorial design."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Garamond. Install on up to 5 computers per user."},
            {"license_type": "webfont", "can_use": CAN_USE_WEBFONT, "cannot_use": CANNOT_USE_WEBFONT,
             "description": "Webfont license for Garamond. Annual license, single domain."},
        ],
    },
    {
        "name": "Futura",
        "foundry": "Bauer Type Foundry",
        "category": "sans-serif",
        "description": (
            "Futura is a geometric sans-serif typeface designed by Paul Renner in 1927. Its clean, "
            "circular forms are inspired by Bauhaus principles, making it a favourite for modern branding."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Futura. Covers personal computers for print and design use."},
            {"license_type": "webfont", "can_use": CAN_USE_WEBFONT, "cannot_use": CANNOT_USE_WEBFONT,
             "description": "Webfont license for Futura. Embed via @font-face on a single domain."},
        ],
    },
    {
        "name": "Bodoni",
        "foundry": "Berthold",
        "category": "serif",
        "description": (
            "Bodoni is a classical serif typeface with extreme contrast between thick and thin strokes. "
            "Designed by Giambattista Bodoni in the late 18th century. Synonymous with luxury and fashion."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Bodoni. Classic serif for print and design use."},
        ],
    },
    {
        "name": "Gill Sans",
        "foundry": "Monotype",
        "category": "sans-serif",
        "description": (
            "Gill Sans is a humanist sans-serif typeface designed by Eric Gill in 1926. It balances "
            "classical letterforms with modern simplicity; strongly associated with British identity."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Gill Sans. Up to 5 installations per user."},
            {"license_type": "webfont", "can_use": CAN_USE_WEBFONT, "cannot_use": CANNOT_USE_WEBFONT,
             "description": "Webfont license for Gill Sans. Annual license, single domain."},
        ],
    },
    {
        "name": "Avenir",
        "foundry": "Linotype",
        "category": "sans-serif",
        "description": (
            "Avenir is a geometric sans-serif typeface designed by Adrian Frutiger in 1988. "
            "Its name means 'future' in French. It is one of Frutiger's favourite typefaces, "
            "balancing the geometric sans-serif with humanist touches for better readability."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Avenir."},
            {"license_type": "webfont", "can_use": CAN_USE_WEBFONT, "cannot_use": CANNOT_USE_WEBFONT,
             "description": "Webfont license for Avenir. Annual license, single domain."},
            {"license_type": "app", "can_use": CAN_USE_APP, "cannot_use": CANNOT_USE_APP,
             "description": "App license for Avenir."},
        ],
    },
    {
        "name": "Caslon",
        "foundry": "Adobe",
        "category": "serif",
        "description": (
            "Caslon is an old-style serif typeface designed by William Caslon in the early 18th century. "
            "Known for warmth, readability, and its role in the American Declaration of Independence."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Caslon."},
        ],
    },
    {
        "name": "Optima",
        "foundry": "Linotype",
        "category": "sans-serif",
        "description": (
            "Optima is a humanist typeface designed by Hermann Zapf in 1952-1955. "
            "It has no serifs but features slightly flared strokes that give it a calligraphic quality. "
            "Used famously on the Vietnam Veterans Memorial."
        ),
        "licenses": [
            {"license_type": "desktop", "can_use": CAN_USE_DESKTOP, "cannot_use": CANNOT_USE_DESKTOP,
             "description": "Desktop license for Optima."},
            {"license_type": "webfont", "can_use": CAN_USE_WEBFONT, "cannot_use": CANNOT_USE_WEBFONT,
             "description": "Webfont license for Optima."},
        ],
    },
]


async def seed_fonts(session: AsyncSession) -> None:
    """Insert catalog fonts if the fonts table is empty."""
    result = await session.execute(select(Font).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    for entry in CATALOG:
        licenses_data = entry.pop("licenses")
        font = Font(**entry)
        session.add(font)
        await session.flush()  # get font.id

        for lic in licenses_data:
            session.add(FontLicense(font_id=font.id, **lic))

    await session.commit()
    print("[seed] Font catalog seeded.")
