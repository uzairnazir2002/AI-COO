"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, MailCheck, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useConfirmRegistration, useResendConfirmation } from "@/features/auth/hooks";

export default function ConfirmPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [email, setEmail] = useState<string | null>(null);
  /** When registration did not pass `?email=`, user can enter an address to resend. */
  const [emailForResend, setEmailForResend] = useState("");
  const confirm = useConfirmRegistration();
  const resend = useResendConfirmation();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setToken(params.get("token") || "");
    setEmail(params.get("email"));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await confirm.mutateAsync({ token });
      router.replace("/auth/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirmation failed");
    }
  }

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="glass-panel panel-edge mx-auto w-full max-w-lg rounded-[32px] p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Confirm account</p>
          <h1 className="mt-3 text-3xl font-semibold">Activate your access</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {email ? `A confirmation token was issued for ${email}.` : "Paste the confirmation token delivered by the email outbox workflow."}
          </p>
          {!email ? (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Need a new token?</p>
              <Input
                type="email"
                autoComplete="email"
                placeholder="Your account email (for resend)"
                value={emailForResend}
                onChange={(e) => setEmailForResend(e.target.value)}
              />
            </div>
          ) : null}
          <form className="mt-8 space-y-4" onSubmit={onSubmit}>
            <Input placeholder="Confirmation token" value={token} onChange={(event) => setToken(event.target.value)} required />
            {error ? <p className="text-sm text-danger">{error}</p> : null}
            <Button className="w-full" disabled={confirm.isPending} type="submit">
              Confirm account <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            {(email || emailForResend.trim()) ? (
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={resend.isPending}
                onClick={() => void resend.mutateAsync({ email: (email || emailForResend.trim()) as string })}
              >
                Resend confirmation token
              </Button>
            ) : null}
            <p className="text-center text-sm text-muted-foreground">
              Already confirmed?{" "}
              <Link className="text-primary underline-offset-4 hover:underline" href="/auth/login">
                Sign in
              </Link>
            </p>
          </form>
        </section>

        <section className="glass-panel panel-edge hidden rounded-[36px] p-8 lg:block">
          <div className="bg-grid rounded-[28px] border border-border/60 p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Verification flow</p>
            <h2 className="mt-4 max-w-xl text-5xl font-semibold leading-tight text-balance">
              Registration now follows the backend confirmation workflow.
            </h2>
            <div className="mt-10 grid gap-4 md:grid-cols-2">
              {[
                { icon: MailCheck, title: "Token delivery", text: "The backend writes a confirmation event into the outbox-backed email flow." },
                { icon: ShieldCheck, title: "Activation gate", text: "Accounts stay inactive until the token is confirmed, matching backend auth rules." },
              ].map((item) => (
                <div key={item.title} className="rounded-[22px] border border-border/60 bg-card/70 p-4">
                  <item.icon className="h-5 w-5 text-primary" />
                  <p className="mt-4 font-medium">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
