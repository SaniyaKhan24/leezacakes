"use client";

import { LoaderCircle, Minus, Plus } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";
import { EASE, FadeIn, SplitText } from "@/components/motion";
import type { Product, SearchResult } from "@/lib/api";
import { money } from "@/lib/format";

export function Button({
  children,
  loading = false,
  variant = "dark",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  variant?: "dark" | "line" | "light";
}) {
  return (
    <button
      {...props}
      className={`btn btn-${variant} ${loading ? "is-loading" : ""} ${className}`}
      disabled={props.disabled || loading}
    >
      <span className="btn-label">{children}</span>
      {loading && (
        <LoaderCircle
          className="spin btn-spinner"
          size={16}
          aria-hidden="true"
        />
      )}
    </button>
  );
}

export function ButtonLink({
  href,
  children,
  variant = "dark",
  className = "",
}: {
  href: string;
  children: ReactNode;
  variant?: "dark" | "line" | "light";
  className?: string;
}) {
  return (
    <Link href={href} className={`btn btn-${variant} ${className}`}>
      <span className="btn-label">{children}</span>
    </Link>
  );
}

/**
 * Django returns absolute media URLs for its own host. Serve them through this
 * site's `/media` proxy instead, so photos load wherever the storefront runs.
 */
export function mediaUrl(src: string | null | undefined) {
  if (!src) return null;
  const match = src.match(/^https?:\/\/[^/]+(\/media\/.*)$/);
  return match ? match[1] : src;
}

/** Product photographs come from Django's media storage through the Next.js proxy. */
export function CakePhoto({
  src: raw,
  alt,
  className = "",
  priority = false,
}: {
  src: string | null | undefined;
  alt: string;
  className?: string;
  priority?: boolean;
}) {
  const src = mediaUrl(raw);
  if (!src)
    return (
      <div
        className={`cake-photo cake-photo-empty ${className}`}
        role="img"
        aria-label={alt}
      />
    );
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className={`cake-photo ${className}`}
      src={src}
      alt={alt}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      fetchPriority={priority ? "high" : "auto"}
    />
  );
}

function images(product: Product | SearchResult) {
  if ("price" in product)
    return { primary: product.primary_image, secondary: null as string | null };
  const sorted = [...(product.images ?? [])].sort(
    (a, b) =>
      Number(b.is_primary) - Number(a.is_primary) ||
      a.sort_order - b.sort_order,
  );
  return {
    primary: product.primary_image?.url ?? sorted[0]?.url ?? null,
    secondary: sorted[1]?.url ?? null,
  };
}

export function productPrice(product: Product | SearchResult) {
  return "price" in product
    ? product.price.amount
    : (product.effective_price ?? product.base_price);
}

export function ProductCard({
  product,
  index = 0,
  size = "regular",
}: {
  product: Product | SearchResult;
  index?: number;
  size?: "regular" | "large";
}) {
  const { primary, secondary } = images(product);
  const amount = productPrice(product);
  const multiple =
    "variants" in product &&
    product.variants.filter((v) => v.is_active).length > 1;
  return (
    <motion.article
      className={`product-card product-card-${size}`}
      layout
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px 0px -6% 0px" }}
      transition={{ duration: 0.9, ease: EASE, delay: (index % 3) * 0.08 }}
    >
      <Link
        href={`/shop/${product.slug}`}
        className="product-card-link"
        data-cursor="View"
      >
        <div className="product-card-media">
          <CakePhoto
            src={primary}
            alt={product.name}
            className="product-card-primary"
          />
          {secondary && (
            <CakePhoto
              src={secondary}
              alt={`${product.name}, cut to show the layers`}
              className="product-card-secondary"
            />
          )}
          <span className="product-card-tag">{product.category.name}</span>
        </div>
        <div className="product-card-body">
          <h3>{product.name}</h3>
          <p className="product-card-price">
            {multiple && <span>from </span>}
            {amount ? money(amount) : "On request"}
          </p>
        </div>
        {"short_description" in product && product.short_description && (
          <p className="product-card-note">{product.short_description}</p>
        )}
      </Link>
    </motion.article>
  );
}

export function PageIntro({
  eyebrow,
  title,
  copy,
  children,
}: {
  eyebrow: string;
  title: string;
  copy?: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-intro">
      <FadeIn>
        <p className="eyebrow">{eyebrow}</p>
      </FadeIn>
      <SplitText as="h1" text={title} />
      {copy && (
        <FadeIn delay={0.25}>
          <p className="page-intro-copy">{copy}</p>
        </FadeIn>
      )}
      {children}
    </header>
  );
}

export function EmptyState({
  title,
  copy,
  href,
  label,
}: {
  title: string;
  copy: string;
  href?: string;
  label?: string;
}) {
  return (
    <FadeIn className="empty-state">
      <h2>{title}</h2>
      <p>{copy}</p>
      {href && <ButtonLink href={href}>{label ?? "Continue"}</ButtonLink>}
    </FadeIn>
  );
}

export function Stepper({
  value,
  onChange,
  min = 1,
  max = 20,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
}) {
  return (
    <div className="stepper" role="group" aria-label="Quantity">
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={disabled || value <= min}
        aria-label="Decrease quantity"
      >
        <Minus size={14} />
      </button>
      <motion.span
        key={value}
        initial={{ y: -8, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="tabular"
      >
        {value}
      </motion.span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={disabled || value >= max}
        aria-label="Increase quantity"
      >
        <Plus size={14} />
      </button>
    </div>
  );
}

export function Field({
  label,
  error,
  hint,
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
}) {
  return (
    <label className={`field ${error ? "has-error" : ""} ${className}`}>
      <span className="field-label">{label}</span>
      <input {...props} aria-invalid={Boolean(error)} />
      {error ? (
        <span className="field-error">{error}</span>
      ) : hint ? (
        <span className="field-hint">{hint}</span>
      ) : null}
    </label>
  );
}

export function TextArea({
  label,
  error,
  hint,
  className = "",
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  error?: string;
  hint?: string;
}) {
  return (
    <label className={`field ${error ? "has-error" : ""} ${className}`}>
      <span className="field-label">{label}</span>
      <textarea {...props} aria-invalid={Boolean(error)} />
      {error ? (
        <span className="field-error">{error}</span>
      ) : hint ? (
        <span className="field-hint">{hint}</span>
      ) : null}
    </label>
  );
}

export function Notice({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "error" | "success";
  children: ReactNode;
}) {
  return (
    <motion.div
      className={`notice notice-${tone}`}
      role={tone === "error" ? "alert" : "status"}
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {children}
    </motion.div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

export function firstError(
  fields: Record<string, string[]> | undefined,
  key: string,
) {
  return fields?.[key]?.[0];
}
