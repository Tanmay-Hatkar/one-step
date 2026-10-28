import { Kitchen } from "@/components/kitchen";
import { SiteFooter } from "@/components/site-footer";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-xl px-4 pt-10 pb-16 sm:pt-16">
      <Kitchen />
      <SiteFooter />
    </main>
  );
}
