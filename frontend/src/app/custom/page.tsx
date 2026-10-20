"use client";
import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { EmptyState, PageIntro, ProductCard } from "@/components/commerce-ui";
import { api, type Product } from "@/lib/api";
export default function CustomPage() { const [products, setProducts] = useState<Product[]>([]); useEffect(() => { api.products("?featured=true").then(setProducts).catch(() => {}); }, []); return <><SiteHeader /><main className="store-main shell"><PageIntro eyebrow="Make it yours" title="Start with a cake, then make it personal." copy="Customization choices are loaded from the bakery for each product. Select a cake below to see what is available." />{products.length ? <div className="shop-grid">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <EmptyState title="Custom options are being prepared." copy="Once products and their compatible options are seeded in the catalogue, you can build your cake here." href="/shop" label="Browse cakes" />}</main></>; }
