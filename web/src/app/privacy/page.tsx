import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = {
  title: "Privacy · One Step",
  description: "What One Step keeps, what it sends to OpenAI, and how to delete it.",
};

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy" updated="14 November 2026">
      <p>
        One Step works without an account. Most of what you do stays in this browser. Here is
        everything that leaves it.
      </p>

      <section>
        <h2>Kept on your device</h2>
        <p>
          Your kitchen (the dishes you cook, your diet choices), saved dishes, recipes you pasted
          and your shopping list are stored in this browser&apos;s local storage. Clearing site data removes them.
        </p>
      </section>

      <section>
        <h2>Sent to OpenAI</h2>
        <p>
          When you describe a dish in your own words, use the microphone, or bring a recipe (pasted
          text or a picture), that text, picture or audio is sent to OpenAI to understand it and to write the differences between
          dishes. If you paste a link, our server opens that page to read the recipe. OpenAI
          processes it under its API terms, which do not use it for training. We keep a cached copy
          of the AI&apos;s answers so the same question doesn&apos;t cost twice. We don&apos;t keep
          your audio or your pictures.
        </p>
      </section>

      <section>
        <h2>Kept on our server, only if you choose</h2>
        <ul>
          <li>
            <strong>Sign in with a passkey</strong> to sync your kitchen. We store a random user id,
            your passkey&apos;s public key and your kitchen. No email, no name, no password. You
            can delete your account and everything with it from the account card.
          </li>
          <li>
            <strong>Share a kitchen link</strong>, and we store the kitchen you shared so the link
            works.
          </li>
          <li>
            <strong>Send feedback</strong>, and we store your message and the page you sent it
            from.
          </li>
        </ul>
      </section>

      <section>
        <h2>Anonymous usage counts</h2>
        <p>
          We count a few actions (a visit, a kitchen built, results shown, a dish opened, cooked
          or saved, a recipe pasted, cook mode used, the app installed, and whether you added a
          name, never the name itself) against a random id made in your browser. It
          doesn&apos;t include anything you type and isn&apos;t linked to an account. Your IP address is used briefly
          to stop abuse and isn&apos;t stored with these counts.
        </p>
      </section>

      <section>
        <h2>Error reports</h2>
        <p>
          When something breaks, a report of the error (what failed, on which page, browser and
          app version) goes to our error tracker, Sentry. It doesn&apos;t include anything you
          type, your recipes, cookies or your IP address.
        </p>
      </section>

      <section>
        <h2>No ads, no selling</h2>
        <p>There are no ads or third-party trackers, and nothing is sold or shared for marketing.</p>
      </section>

      <section>
        <h2>Questions</h2>
        <p>
          Use the Feedback button below. It&apos;s anonymous, so add a way to reach you if
          you&apos;d like a reply.
        </p>
      </section>
    </LegalPage>
  );
}
