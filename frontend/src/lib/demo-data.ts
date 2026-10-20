import type { SearchResult } from "@/lib/api";

/** Development-only presentation data. It is never sent to a backend mutation. */
export const demoProducts: SearchResult[] = [
  { id: "demo-chocolate-truffle", name: "Chocolate Truffle", slug: "demo-chocolate-truffle", category: { name: "Celebration cakes", slug: "celebration-cakes" }, primary_image: null, price: { amount: "850.00", currency: "INR", display_type: "starting_from" }, available: true, match_type: "demo" },
  { id: "demo-belgian-chocolate", name: "Belgian Chocolate", slug: "demo-belgian-chocolate", category: { name: "Chocolate cakes", slug: "chocolate-cakes" }, primary_image: null, price: { amount: "950.00", currency: "INR", display_type: "starting_from" }, available: true, match_type: "demo" },
  { id: "demo-red-velvet", name: "Red Velvet", slug: "demo-red-velvet", category: { name: "Celebration cakes", slug: "celebration-cakes" }, primary_image: null, price: { amount: "800.00", currency: "INR", display_type: "starting_from" }, available: true, match_type: "demo" },
  { id: "demo-vanilla-berry", name: "Vanilla Berry", slug: "demo-vanilla-berry", category: { name: "Fruit cakes", slug: "fruit-cakes" }, primary_image: null, price: { amount: "780.00", currency: "INR", display_type: "starting_from" }, available: true, match_type: "demo" },
  { id: "demo-butterscotch-crunch", name: "Butterscotch Crunch", slug: "demo-butterscotch-crunch", category: { name: "Celebration cakes", slug: "celebration-cakes" }, primary_image: null, price: { amount: "820.00", currency: "INR", display_type: "starting_from" }, available: true, match_type: "demo" },
  { id: "demo-black-forest", name: "Black Forest", slug: "demo-black-forest", category: { name: "Chocolate cakes", slug: "chocolate-cakes" }, primary_image: null, price: { amount: "760.00", currency: "INR", display_type: "starting_from" }, available: true, match_type: "demo" },
];
