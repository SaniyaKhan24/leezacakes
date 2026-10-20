import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider, CartProvider } from "@/components/providers";

export const metadata: Metadata = { title: "Leeza Cakes — Made for your moment", description: "Handcrafted celebration and custom cakes by Leeza Cakes." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AuthProvider><CartProvider>{children}</CartProvider></AuthProvider></body></html>; }
