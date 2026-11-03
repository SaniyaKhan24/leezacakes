"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { FadeIn } from "@/components/motion";

export function useSiteConfig() {
  return useQuery({
    queryKey: ["site"],
    queryFn: api.site,
    staleTime: 10 * 60_000,
  });
}

export function SiteFooter() {
  const { data: site } = useSiteConfig();
  return (
    <footer className="site-footer">
      <div className="shell footer-top">
        <FadeIn className="footer-cta">
          <p className="eyebrow">Planning something?</p>
          <h2>
            Tell us the date.
            <br />
            <em>We&apos;ll bring the cake.</em>
          </h2>
          <Link href="/custom" className="text-link light">
            Start a custom cake
          </Link>
        </FadeIn>
        <div className="footer-columns">
          <div>
            <p className="footer-label">Shop</p>
            <Link href="/shop">All cakes</Link>
            <Link href="/shop?category=celebration">
              Tiered &amp; celebration
            </Link>
            <Link href="/shop?category=bento">Bento &amp; petite</Link>
            <Link href="/custom">Design a cake</Link>
          </div>
          <div>
            <p className="footer-label">Visit</p>
            <p>{site?.pickup_hours_label ?? "Pickup by appointment"}</p>
            {site?.address && <p>{site.address}</p>}
          </div>
          <div>
            <p className="footer-label">Say hello</p>
            {site?.contact_phone && (
              <a href={`tel:${site.contact_phone.replace(/\s/g, "")}`}>
                {site.contact_phone}
              </a>
            )}
            {site?.contact_email && (
              <a href={`mailto:${site.contact_email}`}>{site.contact_email}</a>
            )}
            {site?.instagram && (
              <a
                href={`https://instagram.com/${site.instagram.replace("@", "")}`}
                target="_blank"
                rel="noreferrer"
              >
                {site.instagram}
              </a>
            )}
            <Link href="/contact">Send a message</Link>
            {site?.is_sample && (
              <span className="sample-tag">Sample contact details</span>
            )}
          </div>
        </div>
      </div>
      <div className="footer-wordmark" aria-hidden="true">
        <span>Leeza</span>
        <em>cakes</em>
      </div>
      <div className="shell footer-bottom">
        <span>© {new Date().getFullYear()} Leeza Cakes</span>
        <span>Every cake baked to order</span>
      </div>
    </footer>
  );
}
