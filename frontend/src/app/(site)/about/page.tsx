import type { Metadata } from "next";
import { ButtonLink } from "@/components/commerce-ui";
import { FadeIn, ImageReveal, Marquee, SplitText } from "@/components/motion";

export const metadata: Metadata = { title: "Our story" };

const PRINCIPLES = [
  [
    "Made for the day",
    "We bake to the pickup slot you choose, never ahead for a shelf. That's why each cake asks for a little notice.",
  ],
  [
    "Short ingredient lists",
    "Butter, eggs or our eggless base, flour, sugar, cream, real fruit and good chocolate. Nothing we couldn't explain at the counter.",
  ],
  [
    "Finished by hand",
    "Every kiss, rosette and message is piped by hand, so no two cakes are quite identical — which is rather the point.",
  ],
];

export default function AboutPage() {
  return (
    <main className="page">
      <section className="shell story-hero">
        <div>
          <FadeIn>
            <p className="eyebrow">Our story</p>
          </FadeIn>
          <SplitText
            as="h1"
            text={"A small kitchen,\n*a lot of butter.*"}
            className="display-l"
          />
          <FadeIn delay={0.3}>
            <p className="lede" style={{ marginTop: 30 }}>
              Leeza Cakes began as birthday cakes for friends, then friends of
              friends. Today it&apos;s a small studio that still bakes the same
              way: one order at a time, for one particular day.
            </p>
          </FadeIn>
        </div>
        <ImageReveal className="story-photo">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="cake-photo"
            src="/images/cakes/vanilla-bloom-two-tier-studio.webp"
            alt="A two-tier vanilla cake with sugar roses"
          />
        </ImageReveal>
      </section>
      <div style={{ margin: "var(--section) 0" }}>
        <Marquee
          items={[
            "Birthdays",
            "Anniversaries",
            "Weddings",
            "Office Fridays",
            "Just because",
          ]}
          speed={44}
        />
      </div>
      <section className="shell">
        <div className="story-columns">
          {PRINCIPLES.map(([title, copy], i) => (
            <FadeIn key={title} delay={i * 0.1}>
              <p className="eyebrow">0{i + 1}</p>
              <h3>{title}</h3>
              <p>{copy}</p>
            </FadeIn>
          ))}
        </div>
      </section>
      <section className="shell section" style={{ paddingBottom: 0 }}>
        <FadeIn>
          <p className="quote">
            “The best compliment is an <em>empty plate</em> and someone asking
            who made it.”
          </p>
        </FadeIn>
        <FadeIn
          delay={0.2}
          className="hero-actions"
          style={{ justifyContent: "center", marginTop: 50 }}
        >
          <ButtonLink href="/shop">See the menu</ButtonLink>
        </FadeIn>
      </section>
    </main>
  );
}
