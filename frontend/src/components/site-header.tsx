"use client";
import Link from "next/link";
import { Menu, ShoppingBag, UserRound, X } from "lucide-react";
import { useState } from "react";
import { useAuth, useCart } from "@/components/providers";
import { BrandLogo } from "@/components/brand-logo";
export function SiteHeader() { const [open, setOpen] = useState(false); const { user } = useAuth(); const { cart } = useCart(); return <header className="store-header"><div className="store-nav"><BrandLogo /><nav className={open ? "store-links open" : "store-links"}><Link href="/shop">Shop</Link><Link href="/custom">Custom cakes</Link><Link href="/about">Our story</Link><Link href="/contact">Contact</Link></nav><div className="store-actions"><Link href={user ? "/account" : "/auth/login"} aria-label={user ? "Account" : "Sign in"}><UserRound size={18} /></Link><Link href="/cart" className="cart-link" aria-label="Cart"><ShoppingBag size={18} /><span>{cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0}</span></Link><button className="menu-button" onClick={() => setOpen(!open)} aria-label={open ? "Close menu" : "Open menu"}>{open ? <X size={20} /> : <Menu size={20} />}</button></div></div></header>; }
