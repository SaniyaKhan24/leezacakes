import { ButtonLink } from "@/components/commerce-ui";
import { Assembly } from "@/components/home/assembly";
import { Featured } from "@/components/home/featured";
import { Hero } from "@/components/home/hero";
import { Inside } from "@/components/home/inside";
import { MakeYours } from "@/components/home/make-yours";
import { MenuIndex } from "@/components/home/menu-index";
import { FadeIn, Marquee, SplitText } from "@/components/motion";

const PROCESS = [
  [
    "i",
    "Choose your cake",
    "Pick a size, eggless or not, and any finishing touches. Prices update as you go.",
  ],
  [
    "ii",
    "Pick a pickup slot",
    "Choose a day and an hour. Each cake shows how much notice it needs — tiered cakes need a little more.",
  ],
  [
    "iii",
    "Pay by UPI",
    "Scan the QR on your order page and upload the screenshot. We confirm by hand and start baking.",
  ],
];

export default function Home() {
  return (
    <main>
      <Hero />
      <Marquee
        items={[
          "Baked to order",
          "Eggless on request",
          "Hand-piped",
          "Real butter, real cream",
          "Pickup from the studio",
        ]}
      />
      <MenuIndex />
      <Inside />
      <Featured />
      <Assembly />
      <MakeYours />
      <section className="section shell" aria-labelledby="process-title">
        <div className="section-head">
          <div>
            <FadeIn>
              <p className="eyebrow">How ordering works</p>
            </FadeIn>
            <SplitText text="Three steps, *no phone tag.*" />
          </div>
        </div>
        <div className="process">
          {PROCESS.map(([n, title, copy], i) => (
            <FadeIn key={n} className="process-step" delay={i * 0.12}>
              <span>{n}.</span>
              <h3>{title}</h3>
              <p>{copy}</p>
            </FadeIn>
          ))}
        </div>
      </section>
      <section className="section shell closing">
        <FadeIn>
          <p className="eyebrow">Something sweet in mind?</p>
        </FadeIn>
        <SplitText text={"Let's make\n*your* cake."} />
        <FadeIn
          delay={0.3}
          className="hero-actions"
          style={{ justifyContent: "center" }}
        >
          <ButtonLink href="/shop">Browse the cakes</ButtonLink>
          <ButtonLink href="/contact" variant="line">
            Ask about a wedding cake
          </ButtonLink>
        </FadeIn>
      </section>
    </main>
  );
}
