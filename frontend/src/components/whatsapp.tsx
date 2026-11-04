"use client";

import { AnimatePresence, motion } from "motion/react";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { EASE } from "@/components/motion";
import { useCart } from "@/components/providers";
import { useSiteConfig } from "@/components/site-footer";
import { GENERAL_TEXT, whatsappLink } from "@/lib/whatsapp";

export function WhatsAppGlyph({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.2h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 18.15h-.01a8.23 8.23 0 0 1-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.23 8.25-8.23 2.2 0 4.27.86 5.82 2.42a8.18 8.18 0 0 1 2.41 5.83c0 4.54-3.7 8.22-8.22 8.22Zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.17.24-.64.8-.78.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.5.11-.11.25-.29.37-.43.13-.15.17-.25.25-.42.08-.17.04-.31-.02-.43-.06-.13-.56-1.35-.77-1.85-.2-.48-.41-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.23.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.16-.48-.29Z"
      />
    </svg>
  );
}

/** Returns the click-to-chat URL for a message, or null when no WhatsApp number is configured. */
export function useWhatsApp(text: string) {
  const { data: site } = useSiteConfig();
  return whatsappLink(site?.whatsapp_link_number, text);
}

/** Inline invitation to take a request the app can't handle to WhatsApp. */
export function WhatsAppCta({
  text,
  title = "Want something we don't list?",
  copy = "A photo cake, a theme, a flavour you love — message us on WhatsApp and we'll make it happen.",
  label = "Chat on WhatsApp",
}: {
  text: string;
  title?: string;
  copy?: string;
  label?: string;
}) {
  const href = useWhatsApp(text);
  if (!href) return null;
  return (
    <a className="wa-cta" href={href} target="_blank" rel="noreferrer">
      <span className="wa-cta-icon">
        <WhatsAppGlyph size={22} />
      </span>
      <span className="wa-cta-text">
        <strong>{title}</strong>
        <span>{copy}</span>
      </span>
      <span className="wa-cta-label">{label} →</span>
    </a>
  );
}

/** A floating button on every page, so help is always one tap away. */
export function WhatsAppFab() {
  const href = useWhatsApp(GENERAL_TEXT);
  const { drawerOpen } = useCart();
  const pathname = usePathname();
  const [hover, setHover] = useState(false);
  // The checkout and designer already carry their own WhatsApp prompts.
  const hidden = !href || drawerOpen || pathname.startsWith("/checkout");
  return (
    <AnimatePresence>
      {!hidden && (
        <motion.a
          className="wa-fab"
          href={href!}
          target="_blank"
          rel="noreferrer"
          aria-label="Chat with Leeza Cakes on WhatsApp"
          initial={{ opacity: 0, scale: 0.6, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.6, y: 20 }}
          transition={{ duration: 0.6, ease: EASE, delay: 1.2 }}
          onPointerEnter={() => setHover(true)}
          onPointerLeave={() => setHover(false)}
        >
          <WhatsAppGlyph size={24} />
          <AnimatePresence>
            {hover && (
              <motion.span
                className="wa-fab-label"
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: "auto", opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.35, ease: EASE }}
              >
                Custom order? Chat with us
              </motion.span>
            )}
          </AnimatePresence>
        </motion.a>
      )}
    </AnimatePresence>
  );
}
