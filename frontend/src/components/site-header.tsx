"use client";

import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useScroll,
} from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { BrandLogo } from "@/components/brand-logo";
import { NotificationBell } from "@/components/notification-bell";
import { EASE, EASE_IN_OUT } from "@/components/motion";
import { useAuth, useCart } from "@/components/providers";

const LINKS = [
  { href: "/shop", label: "Shop" },
  { href: "/custom", label: "Design a cake" },
  { href: "/about", label: "Our story" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { count, pulse, setDrawerOpen } = useCart();
  // The menu belongs to the page it was opened on, so navigating closes it.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;
  const setOpen = (next: boolean | ((value: boolean) => boolean)) =>
    setOpenOn(
      (typeof next === "function" ? next(open) : next) ? pathname : null,
    );
  const [hidden, setHidden] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, "change", (latest) => {
    const previous = scrollY.getPrevious() ?? 0;
    setScrolled(latest > 24);
    setHidden(latest > 240 && latest > previous && !open);
  });

  useEffect(() => {
    document.documentElement.classList.toggle("menu-open", open);
  }, [open]);

  return (
    <>
      <motion.header
        className={`site-header ${scrolled ? "is-scrolled" : ""} ${open ? "is-open" : ""}`}
        animate={{ y: hidden ? "-120%" : "0%" }}
        transition={{ duration: 0.6, ease: EASE }}
      >
        <div className="site-header-inner">
          <BrandLogo />
          <nav className="site-nav" aria-label="Primary">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link ${pathname.startsWith(link.href) ? "is-active" : ""}`}
              >
                <span>{link.label}</span>
              </Link>
            ))}
          </nav>
          <div className="site-actions">
            <Link
              href={user ? "/account" : "/auth/login"}
              className="action-link"
            >
              {user ? `Hi, ${user.first_name || "you"}` : "Sign in"}
            </Link>
            <NotificationBell />
            <button
              type="button"
              className="bag-button"
              onClick={() => setDrawerOpen(true)}
              aria-label={`Open bag, ${count} items`}
            >
              <span>Bag</span>
              <motion.span
                key={pulse}
                className="bag-count"
                initial={pulse ? { scale: 1.8 } : false}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 420, damping: 14 }}
              >
                {count}
              </motion.span>
            </button>
            <button
              type="button"
              className="menu-toggle"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={open ? "Close menu" : "Open menu"}
            >
              <span />
              <span />
            </button>
          </div>
        </div>
      </motion.header>
      <AnimatePresence>
        {open && (
          <motion.div
            className="mobile-menu"
            initial={{ clipPath: "inset(0 0 100% 0)" }}
            animate={{ clipPath: "inset(0 0 0% 0)" }}
            exit={{ clipPath: "inset(0 0 100% 0)" }}
            transition={{ duration: 0.8, ease: EASE_IN_OUT }}
          >
            <nav aria-label="Mobile">
              {[
                { href: "/", label: "Home" },
                ...LINKS,
                {
                  href: user ? "/account" : "/auth/login",
                  label: user ? "Account" : "Sign in",
                },
              ].map((link, i) => (
                <motion.div
                  key={link.href}
                  initial={{ y: 60, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{
                    delay: 0.25 + i * 0.06,
                    duration: 0.8,
                    ease: EASE,
                  }}
                >
                  <Link href={link.href} className="mobile-link">
                    <span className="mobile-index">0{i + 1}</span>
                    {link.label}
                  </Link>
                </motion.div>
              ))}
            </nav>
            <p className="mobile-foot">Baked to order · Pickup only</p>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
