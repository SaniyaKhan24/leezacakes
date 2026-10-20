"use client";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, LoaderCircle } from "lucide-react";
import type { Product, SearchResult } from "@/lib/api";
export function Button({ children, loading = false, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) { return <button {...props} className={`shop-button ${props.className ?? ""}`} disabled={props.disabled || loading}>{loading && <LoaderCircle className="spin" size={15} />}{children}</button>; }
export function ProductCard({ product }: { product: Product | SearchResult }) { const image = "price" in product ? product.primary_image : product.primary_image?.url; const amount = "price" in product ? product.price.amount : product.effective_price ?? product.base_price; return <Link className="shop-product" href={`/shop/${product.slug}`}><div className="product-thumb">{image ? <Image src={image} alt={product.name} fill sizes="(max-width: 700px) 100vw, 33vw" /> : <span>{product.name}<small>image placeholder</small></span>}</div><div className="product-line"><div><h3>{product.name}</h3><p>{product.category.name}</p></div><strong>{amount ? `₹${Number(amount).toLocaleString("en-IN")}` : "Price on request"}</strong></div></Link>; }
export function PageIntro({ eyebrow, title, copy }: { eyebrow: string; title: string; copy?: string }) { return <div className="page-intro"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{copy && <p>{copy}</p>}</div>; }
export function EmptyState({ title, copy, href, label }: { title: string; copy: string; href?: string; label?: string }) { return <div className="empty-state"><h2>{title}</h2><p>{copy}</p>{href && <Link className="shop-button" href={href}>{label ?? "Continue"}<ArrowRight size={16} /></Link>}</div>; }
