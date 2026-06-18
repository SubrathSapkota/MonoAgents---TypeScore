-- ============================================================
-- TypeScore Font Dashboard — Database Schema
-- Database: hackathon (PostgreSQL)
-- ============================================================

-- Create the database (run as superuser once):
-- CREATE DATABASE hackathon;

-- ──────────────────────────────────────────────────────────────
-- USERS
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ──────────────────────────────────────────────────────────────
-- FONT CATALOG  (master list of known fonts)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fonts (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    foundry     VARCHAR(255),
    category    VARCHAR(100),          -- sans-serif | serif | display | monospace | script
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ──────────────────────────────────────────────────────────────
-- FONT LICENSES  (per font × per license type)
-- license_type: desktop | webfont | app | edoc | digital_ad
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS font_licenses (
    id           SERIAL PRIMARY KEY,
    font_id      INTEGER NOT NULL REFERENCES fonts(id) ON DELETE CASCADE,
    license_type VARCHAR(50) NOT NULL,
    can_use      JSONB NOT NULL DEFAULT '[]',
    cannot_use   JSONB NOT NULL DEFAULT '[]',
    description  TEXT,
    eula_url     VARCHAR(500),
    UNIQUE (font_id, license_type)
);

-- ──────────────────────────────────────────────────────────────
-- USER FONT LIBRARY  (fonts a user has acquired / uploaded)
-- source: 'catalog' | 'upload' | 'manual'
-- font_id is set when font exists in catalog; otherwise custom_font_name holds the name
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_fonts (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    font_id          INTEGER REFERENCES fonts(id) ON DELETE SET NULL,
    custom_font_name VARCHAR(255),
    license_type     VARCHAR(50),    -- which license type this user holds
    source           VARCHAR(50) NOT NULL DEFAULT 'manual',
    added_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT chk_font_source CHECK (
        font_id IS NOT NULL OR custom_font_name IS NOT NULL
    )
);

-- ──────────────────────────────────────────────────────────────
-- SCAN RESULTS  (history of every URL analysis)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scan_results (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER REFERENCES users(id) ON DELETE SET NULL,
    url                  VARCHAR(500) NOT NULL,
    overall_score        NUMERIC(5,1),
    brand_consistency    NUMERIC(5,1),
    license_compliance   NUMERIC(5,1),
    performance          NUMERIC(5,1),
    accessibility        NUMERIC(5,1),
    developer_experience NUMERIC(5,1),
    issues               JSONB NOT NULL DEFAULT '[]',
    raw_data             JSONB NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Future: brand guidelines (PDF upload placeholder)
-- This table is intentionally left for Phase 2
CREATE TABLE IF NOT EXISTS brand_guidelines (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name   VARCHAR(255) NOT NULL,
    file_size   INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    parsed_data JSONB           -- extracted font rules, color palettes, etc.
);


-- ============================================================
-- SEED DATA — Font Catalog
-- ============================================================

-- ── Helvetica ───────────────────────────────────────────────
INSERT INTO fonts (id, name, foundry, category, description) VALUES
(1, 'Helvetica', 'Linotype', 'sans-serif',
 'Helvetica is one of the most widely used typefaces in the world. Designed in 1957 by Max Miedinger, its clean, neutral forms have made it a staple of graphic design and corporate identity.');

-- Helvetica Desktop License
INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(1, 'desktop',
 '[
   {"name": "Videos", "description": "Apply fonts in titles, credits, and on-screen text."},
   {"name": "PDFs", "description": "Style reports, brochures, and digital documents."},
   {"name": "Greeting cards", "description": "Design unique, personalized cards for any occasion."},
   {"name": "Logos", "description": "Craft memorable, professional logo typography."},
   {"name": "Signage (wayfinding & billboards)", "description": "Make clear, eye-catching signage for indoor or outdoor use."},
   {"name": "Flyers", "description": "Set readable, attractive headlines and layouts."},
   {"name": "Packaging", "description": "Enhance product packaging with stylish text."},
   {"name": "Album covers", "description": "Print custom text designs on album artwork."},
   {"name": "Posters", "description": "Bold, eye-catching poster layouts."},
   {"name": "Invitations", "description": "Create stylish, personalized invitations for events."},
   {"name": "Social posts", "description": "Enhance graphics and captions with unique fonts."},
   {"name": "Business cards", "description": "Craft professional, memorable business card designs."},
   {"name": "School projects", "description": "Make projects stand out with creative text."},
   {"name": "Wordmarks", "description": "Develop strong, recognizable brand wordmarks."},
   {"name": "Stationery", "description": "Design elegant letterheads, envelopes, and notes."}
 ]',
 '[
   {"name": "E-books", "description": "Fonts cannot be embedded in digital books.", "link": "View relevant license"},
   {"name": "Digital ads", "description": "Ads cannot use these fonts.", "link": "View relevant license"},
   {"name": "Commercial print environments", "description": "Not for large-scale printing business."},
   {"name": "Websites", "description": "Fonts cannot be hosted online.", "link": "View web font license"},
   {"name": "Emails", "description": "Fonts not allowed in email templates.", "link": "Learn more"},
   {"name": "Apps", "description": "Cannot embed fonts inside applications.", "link": "View app license"},
   {"name": "Sharing the font", "description": "Fonts cannot be distributed to others."},
   {"name": "Allowing others to use the font", "description": "License is for you only."},
   {"name": "Collaboration", "description": "Fonts cannot be shared in teams.", "link": "Learn more"},
   {"name": "Modifying", "description": "Fonts cannot be altered or edited.", "link": "Learn more"},
   {"name": "Installation on a server", "description": "Fonts cannot be installed on a server."},
   {"name": "AI training", "description": "Fonts not permitted for AI models."},
   {"name": "DAMs", "description": "Fonts cannot be hosted on DAMs as downloadable assets."}
 ]',
 'A Desktop license allows you to install the font on your computer and use it in desktop applications such as word processors, design tools, and print workflows. This license is per user per computer.'
);

-- Helvetica Webfont License
INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(1, 'webfont',
 '[
   {"name": "Website typography", "description": "Embed via @font-face for headings and body text on a single domain."},
   {"name": "Landing pages", "description": "Use on marketing and product landing pages."},
   {"name": "Web applications", "description": "Style text in browser-based applications."},
   {"name": "Responsive layouts", "description": "Works across desktop, tablet, and mobile viewports."}
 ]',
 '[
   {"name": "Multiple domains", "description": "A single webfont license covers one domain only."},
   {"name": "Agency sharing", "description": "Web agencies may not share a single license across client sites."},
   {"name": "Logo-only use", "description": "If the font is only in a graphic/logo, purchase a Desktop license instead."},
   {"name": "Embedding in apps", "description": "Use an App license for mobile or desktop applications.", "link": "View app license"},
   {"name": "Email templates", "description": "Not permitted in HTML emails."},
   {"name": "Redistribution", "description": "Font files may not be distributed to end users."}
 ]',
 'Webfonts allow you to embed the font into a webpage using the @font-face rule. You will be serving the webfont kit for your own site. Most foundries offer webfonts with an Annual license model.'
);

-- Helvetica App License
INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(1, 'app',
 '[
   {"name": "iOS apps", "description": "Embed the font in your Apple App Store application."},
   {"name": "Android apps", "description": "Bundle the font in your Google Play application."},
   {"name": "Windows Phone apps", "description": "Include the font in Windows Phone applications."},
   {"name": "Cross-platform apps", "description": "Use in React Native, Flutter, or similar cross-platform builds."}
 ]',
 '[
   {"name": "Desktop software", "description": "Use a Desktop license for desktop applications."},
   {"name": "Websites", "description": "Use a Webfont license for browser-based use."},
   {"name": "Redistribution", "description": "Font files may not be extracted or redistributed."},
   {"name": "Unlimited installs", "description": "App license is priced per app, per platform tier."}
 ]',
 'Select this license when developing an app for iOS, Android, or Windows Phone and embedding the font file in your mobile application code.'
);

-- Helvetica Electronic Doc License
INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(1, 'edoc',
 '[
   {"name": "eBooks", "description": "Embed in EPUB, MOBI, or PDF-based digital books."},
   {"name": "eMagazines", "description": "Style digital magazine issues with embedded fonts."},
   {"name": "eNewspapers", "description": "Use in digital newspaper publications."},
   {"name": "Digital annual reports", "description": "Produce interactive or PDF-based annual reports."}
 ]',
 '[
   {"name": "Multiple publications", "description": "Each issue/volume counts as a separate publication requiring its own license."},
   {"name": "Free updates redistribution", "description": "Updated versions free to previous customers do not need a new license; otherwise each new version does."},
   {"name": "Cover art only", "description": "For font usage in ePub cover graphics only, use a Desktop license instead."},
   {"name": "Print books", "description": "Not for physical / print-on-demand books."}
 ]',
 'An Electronic Doc license lets you embed the font in an electronic publication. Priced per number of publications. Regional or format variations of the same issue do not count as separate publications.'
);

-- Helvetica Digital Ad License
INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(1, 'digital_ad',
 '[
   {"name": "HTML5 banner ads", "description": "Embed webfonts in HTML5 animated banner ads."},
   {"name": "Programmatic ads", "description": "Use in display ads served across advertising networks."},
   {"name": "Rich media ads", "description": "Use in interactive or expandable ad units."},
   {"name": "Agency-produced creatives", "description": "Kit may be shared with third parties producing ads on your behalf."}
 ]',
 '[
   {"name": "Websites", "description": "Use a Webfont license for website usage instead."},
   {"name": "Unlimited impressions without true-up", "description": "Impressions must be tracked; true-up at end of campaign if volume was unknown."},
   {"name": "Redistribution beyond ad creatives", "description": "Font kit shared with third parties is for ad creative production only."}
 ]',
 'Use this license to embed fonts in digital ads such as HTML5 banners. Priced per impression tier. Agencies producing ads on your behalf may receive the kit but you remain responsible for compliance.'
);


-- ── Garamond ────────────────────────────────────────────────
INSERT INTO fonts (id, name, foundry, category, description) VALUES
(2, 'Garamond', 'Adobe', 'serif',
 'Garamond is a classic old-style serif typeface named after the 16th century French punch-cutter Claude Garamond. It is known for its elegance and legibility, widely used in book and editorial design.');

INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(2, 'desktop',
 '[
   {"name": "Books & editorial", "description": "Set body text and headings in print publications."},
   {"name": "Brand identity", "description": "Use for brand marks, logos, and wordmarks."},
   {"name": "PDFs & reports", "description": "Style corporate documents and reports."},
   {"name": "Packaging", "description": "Apply to product packaging and labels."},
   {"name": "Stationery", "description": "Use on letterheads, business cards, and envelopes."}
 ]',
 '[
   {"name": "Websites", "description": "Requires separate Webfont license."},
   {"name": "Apps", "description": "Requires separate App license."},
   {"name": "E-books", "description": "Requires Electronic Doc license."},
   {"name": "Server installation", "description": "Not permitted on servers."}
 ]',
 'Desktop license for Garamond. Install on up to 5 computers per user.'
);


-- ── Futura ─────────────────────────────────────────────────
INSERT INTO fonts (id, name, foundry, category, description) VALUES
(3, 'Futura', 'Bauer Type Foundry', 'sans-serif',
 'Futura is a geometric sans-serif typeface designed by Paul Renner in 1927. Its clean, circular forms are inspired by Bauhaus principles, making it a favourite for modern, minimalist brand identity.');

INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(3, 'desktop',
 '[
   {"name": "Logos & wordmarks", "description": "Ideal for strong, geometric brand marks."},
   {"name": "Posters & signage", "description": "Works beautifully at large display sizes."},
   {"name": "Packaging", "description": "Apply to product packaging with modern aesthetic."},
   {"name": "Print advertising", "description": "Use in print campaigns and brochures."},
   {"name": "Videos & motion", "description": "Title cards, lower thirds, and credits."}
 ]',
 '[
   {"name": "Websites", "description": "Webfont license required."},
   {"name": "Digital ads", "description": "Digital Ad license required."},
   {"name": "Apps", "description": "App license required."}
 ]',
 'Desktop license for Futura. Covers personal computers for print and static design use.'
);

INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(3, 'webfont',
 '[
   {"name": "Website headings", "description": "Use for impactful display and headline text on websites."},
   {"name": "Marketing sites", "description": "Perfect for product and brand marketing pages."},
   {"name": "Portfolio sites", "description": "Showcase creative work with strong typography."}
 ]',
 '[
   {"name": "Multiple domains", "description": "One license per domain."},
   {"name": "Email templates", "description": "Not permitted in email."},
   {"name": "Redistribution", "description": "Font files may not be served directly to end users."}
 ]',
 'Webfont license for Futura. Embed via @font-face on a single domain. Annual license model.'
);


-- ── Bodoni ─────────────────────────────────────────────────
INSERT INTO fonts (id, name, foundry, category, description) VALUES
(4, 'Bodoni', 'Berthold', 'serif',
 'Bodoni is a classical serif typeface with extreme contrast between thick and thin strokes, designed by Giambattista Bodoni in the late 18th century. It is synonymous with luxury, fashion, and editorial elegance.');

INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(4, 'desktop',
 '[
   {"name": "Fashion & luxury branding", "description": "The go-to for high-fashion logos and editorial."},
   {"name": "Magazine layouts", "description": "Excellent for editorial headlines and pull quotes."},
   {"name": "Invitations & stationery", "description": "Elegant choice for formal events."},
   {"name": "Packaging", "description": "Luxury product packaging and labels."},
   {"name": "Posters", "description": "Dramatic poster designs with high contrast."}
 ]',
 '[
   {"name": "Digital ads", "description": "Requires Digital Ad license."},
   {"name": "Websites", "description": "Webfont license required for web use."},
   {"name": "Modifying the font", "description": "Font files cannot be altered."}
 ]',
 'Desktop license for Bodoni. Classic serif for print and design use.'
);


-- ── Gill Sans ─────────────────────────────────────────────
INSERT INTO fonts (id, name, foundry, category, description) VALUES
(5, 'Gill Sans', 'Monotype', 'sans-serif',
 'Gill Sans is a humanist sans-serif typeface designed by Eric Gill in 1926. It balances classical letterforms with modern simplicity and is strongly associated with British identity and transport signage.');

INSERT INTO font_licenses (font_id, license_type, can_use, cannot_use, description) VALUES
(5, 'desktop',
 '[
   {"name": "Corporate identity", "description": "Reliable and professional for corporate branding."},
   {"name": "Transport & wayfinding", "description": "Excellent legibility for signage systems."},
   {"name": "Books & publications", "description": "Clean body text for long-form reading."},
   {"name": "UI mockups", "description": "Use in design mockups and prototypes (not embedded)."},
   {"name": "Stationery & print", "description": "Business cards, letterheads, and envelopes."}
 ]',
 '[
   {"name": "Web embedding", "description": "Webfont license required."},
   {"name": "App embedding", "description": "App license required."},
   {"name": "AI training", "description": "Font not permitted for AI model training."}
 ]',
 'Desktop license for Gill Sans. Up to 5 installations per user.'
);

-- Reset sequence to avoid conflicts with auto-inserted IDs
SELECT setval('fonts_id_seq', 10, true);
