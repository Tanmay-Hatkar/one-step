import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

/** Crawl the public pages; keep personal ones (shared kitchens, saved) out of search. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/k/", "/saved"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
