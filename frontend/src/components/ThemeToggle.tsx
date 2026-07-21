"use client";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "./ui/Button";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className="fixed top-4 right-4 z-50 h-9 w-9 rounded-full" />;
  }

  return (
    <Button
      variant="outline"
      size="icon"
      className="fixed top-4 right-4 z-50 h-9 w-9 rounded-full"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
