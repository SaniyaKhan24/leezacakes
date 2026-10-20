import Image from "next/image";
import { ArrowUpRight, Star } from "lucide-react";

import { SiteHeader } from "@/components/site-header";
import { Reveal } from "@/components/reveal";
import { fetchCatalog, type Product } from "@/lib/catalog";

const occasions = [
  { number: "01", title: "Birthdays", copy: "A little more joy for their day.", tone: "rose" },
  { number: "02", title: "Milestones", copy: "Mark the moments worth remembering.", tone: "sand" },
  { number: "03", title: "Just Because", copy: "The sweetest surprises need no reason.", tone: "gold" },
];
const gallery = ["Floral detail", "A table set for something sweet", "Hand-finished texture"];

export default async function Home() {
  const { products, categories } = await fetchCatalog();
  const featured = products.filter((product) => product.is_featured).slice(0, 3);
  const displayedProducts = (featured.length ? featured : products).slice(0, 3);
  return (
    <main>
      <SiteHeader />
      <section className="hero shell" id="top">
        <div className="hero-copy"><Reveal><p className="eyebrow">Small batch · made with care</p><h1>Every celebration deserves a <em>beautiful cake.</em></h1><p className="hero-intro">Handcrafted cakes for the moments that deserve something special.</p><div className="button-row"><a className="button button-dark" href="#cakes">Explore our cakes <ArrowUpRight size={16} /></a><a className="button button-line" href="#custom">Create a custom cake <ArrowUpRight size={16} /></a></div></Reveal><Reveal delay="delay-2"><div className="hero-note"><span>01</span><p>Thoughtful details.<br />Memorable flavours.</p></div></Reveal></div>
        <Reveal className="hero-visual" delay="delay-1"><div className="image-placeholder hero-image" role="img" aria-label="Replaceable signature cake photography placeholder"><span>Signature cake<br /><small>photography placeholder</small></span></div><div className="image-caption"><span>Leeza Cakes</span><span>Made for your moment</span></div></Reveal>
      </section>
      <section className="section shell" id="occasions"><Reveal className="section-heading split-heading"><div><p className="eyebrow">Find your moment</p><h2>Shop by <em>occasion.</em></h2></div><p className="section-lede">Whatever you’re celebrating, there’s a cake waiting to make it feel a little more magical.</p></Reveal><div className="occasion-grid">{occasions.map((occasion, index) => <Reveal key={occasion.title} delay={`delay-${index + 1}`}><a className={`occasion-card ${occasion.tone}`} href="#cakes"><span className="card-number">{occasion.number}</span><div><h3>{categories[index]?.name ?? occasion.title}</h3><p>{occasion.copy}</p></div><ArrowUpRight className="card-arrow" size={20} /></a></Reveal>)}</div></section>
      <section className="section shell" id="cakes"><Reveal className="section-heading split-heading"><div><p className="eyebrow">The edit</p><h2>Featured <em>cakes.</em></h2></div><a className="text-link" href="#custom">View all cakes <ArrowUpRight size={16} /></a></Reveal>{displayedProducts.length > 0 ? <div className="product-grid">{displayedProducts.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div> : <div className="catalog-empty"><p className="eyebrow">Coming from the kitchen</p><h3>Our first collection is being finished with care.</h3><p>Product photography and live catalogue pricing will appear here once the catalogue is seeded.</p></div>}</section>
      <section className="spotlight shell"><Reveal className="spotlight-image"><div className="image-placeholder editorial-image" role="img" aria-label="Replaceable editorial cake photography placeholder"><span>Editorial cake<br /><small>photography placeholder</small></span></div></Reveal><Reveal className="spotlight-copy" delay="delay-1"><p className="eyebrow">The Leeza signature</p><h2>Made to be <em>remembered.</em></h2><p>From the first sketch to the final flourish, every Leeza cake is made slowly, thoughtfully, and with a little room for wonder.</p><a className="text-link" href="#custom">Discover our craft <ArrowUpRight size={16} /></a></Reveal></section>
      <section className="custom-section" id="custom"><div className="shell custom-inner"><Reveal><p className="eyebrow eyebrow-light">Made just for you</p><h2>Your story.<br /><em>Our canvas.</em></h2></Reveal><Reveal delay="delay-1"><p className="custom-copy">Tell us what you’re celebrating, and we’ll help you create a cake that feels entirely yours.</p><a className="button button-light" href="#contact">Start a conversation <ArrowUpRight size={16} /></a></Reveal></div></section>
      <section className="section shell" id="craft"><Reveal className="section-heading split-heading"><div><p className="eyebrow">Behind the scenes</p><h2>Our <em>craft.</em></h2></div><p className="section-lede">A glimpse at the hands, ingredients, and little rituals behind every bake.</p></Reveal><div className="gallery-grid">{gallery.map((label, index) => <Reveal key={label} className={`gallery-item gallery-${index + 1}`} delay={`delay-${index + 1}`}><div className="image-placeholder" role="img" aria-label={`Replaceable ${label} photography placeholder`}><span>{label}<small>photography placeholder</small></span></div></Reveal>)}</div></section>
      <section className="reviews shell"><Reveal><p className="eyebrow">Kind words</p><div className="stars" aria-label="Five stars"><Star fill="currentColor" size={15} /><Star fill="currentColor" size={15} /><Star fill="currentColor" size={15} /><Star fill="currentColor" size={15} /><Star fill="currentColor" size={15} /></div><blockquote>“The cake was as beautiful as it was delicious. It made the whole room pause.”</blockquote><p className="reviewer">— A happy celebration</p></Reveal></section>
      <section className="final-cta shell"><Reveal><p className="eyebrow">Let’s make it special</p><h2>Have something sweet<br /><em>in mind?</em></h2><a className="button button-dark" href="#contact">Get in touch <ArrowUpRight size={16} /></a></Reveal></section>
      <footer className="footer" id="contact"><div className="shell footer-grid"><div><a className="logo footer-logo" href="#top">leeza<span>cakes</span></a><p className="footer-note">Celebration cakes,<br />made with feeling.</p></div><div><p className="footer-label">Explore</p><a href="#cakes">Cakes</a><a href="#occasions">Occasions</a><a href="#custom">Custom cakes</a></div><div><p className="footer-label">Say hello</p><p className="footer-contact-pending">Contact details will be added here once configured.</p></div></div><div className="shell footer-bottom"><span>© Leeza Cakes</span></div></footer>
    </main>
  );
}

function ProductCard({ product, index }: { product: Product; index: number }) {
  const image = product.primary_image?.url || product.images[0]?.url;
  return <Reveal className="product-card" delay={`delay-${index + 1}`}><a href={`/cakes/${product.slug}`} className="product-image">{image ? <Image src={image} alt={product.primary_image?.alt_text || product.name} fill sizes="(max-width: 768px) 100vw, 33vw" /> : <div className="image-placeholder"><span>{product.name}<small>photography placeholder</small></span></div>}</a><div className="product-meta"><div><h3>{product.name}</h3><p>{product.short_description || product.description}</p></div><span>{formatPrice(product.effective_price ?? product.base_price, product.currency)}</span></div></Reveal>;
}
function formatPrice(price: string | null, currency: string) { return price ? new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(price)) : "Price on request"; }
