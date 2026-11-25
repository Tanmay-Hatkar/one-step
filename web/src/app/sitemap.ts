import type { MetadataRoute } from "next";

import { fetchDishIndex } from "@/lib/dish-data";
import { SITE_URL } from "@/lib/site";

/** Every public page: the app, the directory, and one page per catalog dish. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const dishes = await fetchDishIndex();
  return [
    { url: SITE_URL, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/dishes`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITE_URL}/evals`, changeFrequency: "monthly", priority: 0.3 },
    ...dishes.map((d) => ({
      url: `${SITE_URL}/dish/${d.id}`,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ];
}
