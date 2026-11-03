import { CartDrawer } from "@/components/cart-drawer";
import { Cursor, SmoothScroll } from "@/components/motion";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export default function SiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SmoothScroll>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <SiteHeader />
      <div id="main">{children}</div>
      <SiteFooter />
      <CartDrawer />
      <Cursor />
      <div className="grain" aria-hidden="true" />
    </SmoothScroll>
  );
}
