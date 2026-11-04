"use client";

import { EnquiryForm } from "@/components/enquiry-form";
import { FadeIn, SplitText } from "@/components/motion";
import { useSiteConfig } from "@/components/site-footer";
import { WhatsAppCta } from "@/components/whatsapp";
import { GENERAL_TEXT } from "@/lib/whatsapp";

export default function ContactPage() {
  const { data: site } = useSiteConfig();
  const rows = [
    ["Call or WhatsApp", site?.contact_phone],
    ["Email", site?.contact_email],
    ["Studio", site?.address],
    ["Pickup hours", site?.pickup_hours_label],
  ].filter(([, v]) => v) as [string, string][];
  return (
    <main className="page shell">
      <div className="contact-grid">
        <div>
          <FadeIn>
            <p className="eyebrow">Contact</p>
          </FadeIn>
          <SplitText
            as="h1"
            text={"Tell us what\n*you're celebrating.*"}
            className="display-m"
          />
          <FadeIn delay={0.25}>
            <p className="lede" style={{ margin: "28px 0 48px" }}>
              Questions about an order, a flavour or a date? Write to us here —
              or start a bespoke cake and tell us everything.
            </p>
            <dl className="contact-list">
              {rows.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            <div style={{ marginTop: 32 }}>
              <WhatsAppCta
                title="Fastest: WhatsApp"
                copy="Send a photo of what you have in mind and we'll reply with ideas and a price."
                text={GENERAL_TEXT}
              />
            </div>
            {site?.is_sample && (
              <span className="sample-tag">Sample contact details</span>
            )}
          </FadeIn>
        </div>
        <FadeIn delay={0.15}>
          <EnquiryForm />
        </FadeIn>
      </div>
    </main>
  );
}
