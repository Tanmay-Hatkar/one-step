import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = {
  title: "Terms · One Step",
  description: "The plain terms for using One Step.",
};

export default function TermsPage() {
  return (
    <LegalPage title="Terms" updated="5 November 2026">
      <p>One Step is a free side project. By using it you agree to these terms.</p>

      <section>
        <h2>Suggestions, not guarantees</h2>
        <p>
          Dishes and the differences between them are written with help from AI. They can be wrong
          about ingredients, quantities, times or methods. Use your own judgement in the kitchen,
          and cook meat, fish and eggs to safe temperatures.
        </p>
      </section>

      <section>
        <h2>Allergies and diets</h2>
        <p>
          Diet filters check each dish&apos;s listed ingredients, but they can&apos;t know
          what&apos;s in the products you buy. If you have an allergy, always read the labels. Don&apos;t
          rely on One Step for medical or dietary advice.
        </p>
      </section>

      <section>
        <h2>Fair use</h2>
        <p>
          Don&apos;t abuse the service, scrape it or try to break it. There are rate limits, and
          we may block traffic that looks automated.
        </p>
      </section>

      <section>
        <h2>No warranty</h2>
        <p>
          One Step is provided as is. It may change, go down or stop at any time. Keep anything
          important somewhere else too. To the extent the law allows, we aren&apos;t liable for
          losses from using it.
        </p>
      </section>

      <section>
        <h2>Your data</h2>
        <p>
          See the <a href="/privacy" className="underline underline-offset-2">privacy page</a>.
        </p>
      </section>
    </LegalPage>
  );
}
