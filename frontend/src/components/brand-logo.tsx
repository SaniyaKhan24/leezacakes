import Image from "next/image";
import Link from "next/link";

export function BrandLogo({ className = "", href = "/" }: { className?: string; href?: string }) {
  return (
    <Link className={`brand-logo ${className}`.trim()} href={href} aria-label="Leeza Cakes home">
      <Image className="brand-logo-image" src="/images/brand/leeza-logo.png" alt="Leeza Cakes" width={2158} height={729} priority />
    </Link>
  );
}
