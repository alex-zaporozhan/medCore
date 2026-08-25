# Why MedCore exists

This is the origin note for people who arrived from [LEO](https://github.com/alex-zaporozhan/leo) or from a link on Hacker News. The product map is in [`PRODUCT_OVERVIEW.md`](./PRODUCT_OVERVIEW.md). This file is only the *why*.

## The wall

I started software work between intern and junior, during the hiring freeze that has defined this market for the last few years. The catch-22 is specific: you cannot get hired without production experience, and you cannot get production experience without being hired. Katas and tutorial CRUDs do not count. They never had to protect an invariant while two requests raced.

That was not only a money problem. It was a quiet, ongoing doubt about whether the path was still open at all, when every door that would let you prove yourself asked for the proof first.

## The bet

The industry was not going to hand over a team. A coding agent could write code, but it had no engineering department to write that code *inside of*. So the bet was: build the department as text, and let the agent supply the reps the market would not.

I did not already possess, as skill, the knowledge this class of system requires — tenancy, concurrency, RBAC drift, outbox delivery, lock lifetimes, an adversarial pass that is not the same pass that wrote the feature. I knew those things existed and that they decide whether a clinic OS holds. I did not have them in my hands. Writing them down as rules the agent had to load *before* it typed was how I organized knowledge I was still acquiring, while still shipping something that would punish a guess.

That written department is **LEO**. MedCore is the first product it ran end-to-end, when the constitution was thinner than the 41 laws and 22 roles in the public LEO repository today. Most of those laws are scar tissue from this repo and from the work that followed it. A double-booked slot is why "an `if` is not a lock" became a standing rule. A raw id in an admin table is why "no UUIDs in the UI" is a blocker, not a style nit.

## What "AI-authored" means here

It does not mean a hosted no-code builder. It does not mean "I accepted whatever the chat returned."

It means:

1. I sat as tech lead: route the work, refuse incomplete gates, publish history.
2. The agent wrote the application code, under a role that is the only role allowed to touch code.
3. Architecture, invariants, QA, and security were separate passes with written artifacts — not vibes in the same breath as the patch.
4. I never treated "the agent said it's done" as done.

LEO was less developed then. This repository reads that way in places. I am publishing it with those flaws intact. A debut that survived messy real data at build time is more informative than a flagship polished after the fact.

The longer argument about context drift, amnesia, and why "treat the model like a junior" is the wrong model lives in the [LEO manifesto](https://github.com/alex-zaporozhan/leo/blob/main/MANIFESTO.md).

— Alexandr Zaporojan
