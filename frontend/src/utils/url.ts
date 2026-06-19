export type UrlValidationResult =
  | { valid: true; url: string }
  | { valid: false; message: string };

export function parseWebsiteUrl(raw: string): UrlValidationResult {
  const trimmed = raw.trim();

  if (!trimmed) {
    return { valid: false, message: "Please enter a website URL." };
  }

  if (/\s/.test(trimmed)) {
    return { valid: false, message: "URLs cannot contain spaces." };
  }

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;

  let parsed: URL;
  try {
    parsed = new URL(withProtocol);
  } catch {
    return {
      valid: false,
      message: "Please enter a valid URL (e.g. example.com or https://example.com).",
    };
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return { valid: false, message: "Only http and https URLs are supported." };
  }

  const hostname = parsed.hostname;
  if (!hostname) {
    return { valid: false, message: "Please enter a valid website address." };
  }

  if (hostname === "localhost" || hostname.endsWith(".localhost")) {
    return { valid: true, url: parsed.href };
  }

  if (hostname.includes(":")) {
    return { valid: true, url: parsed.href };
  }

  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(hostname)) {
    return { valid: true, url: parsed.href };
  }

  if (!hostname.includes(".")) {
    return {
      valid: false,
      message: "Please enter a full domain name (e.g. example.com).",
    };
  }

  const domainPattern =
    /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$/i;
  if (!domainPattern.test(hostname)) {
    return { valid: false, message: "Please enter a valid website address." };
  }

  return { valid: true, url: parsed.href };
}
