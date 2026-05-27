"use client"

import type React from "react"
import { useState } from "react"
import { ChevronDown } from "lucide-react"

const faqData = [
  {
    question: "What is Argus and who is it for?",
    answer:
      "Argus is a multi-agent AI platform that automates code review at the pull-request level. It's designed for individual developers who want faster, more consistent reviews, and engineering teams that need security coverage, quality gates, and ticket compliance without adding manual overhead.",
  },
  {
    question: "How does Argus's AI code review work?",
    answer:
      "When a pull request is opened, Argus receives the GitHub webhook, fetches the diff, and dispatches five specialized agents in parallel: Security, Quality, Testing, Documentation, and Ticket Compliance. Each agent analyzes its domain and returns structured findings. The Fix Engine then generates validated, multi-language patches and posts everything as native GitHub review comments and suggestion blocks.",
  },
  {
    question: "Can I integrate Argus with my existing tools?",
    answer:
      "Yes. Argus installs as a GitHub App in two clicks with minimum required permissions. Team and Enterprise plans also integrate with Linear, Jira, Slack, and Notion for ticket compliance and notifications. No CI changes or config files required.",
  },
  {
    question: "What's included in the free plan?",
    answer:
      "The free plan includes 50 reviews per month, the Security, Quality, and Testing agents, GitHub inline suggestions, and the Fix Engine. It's permanent — not a trial — and works with any GitHub repository.",
  },
  {
    question: "How do the parallel agents work?",
    answer:
      "All five agents fan out simultaneously via a LangGraph graph. They don't run sequentially or share state — each one gets the same diff and works independently. Findings are merged by a reducer and posted as a single, grouped GitHub review comment plus inline suggestions. Average review time is 4.2 seconds.",
  },
  {
    question: "Is my code secure with Argus?",
    answer:
      "Argus uses the minimum GitHub App permissions required: read diffs and post review comments. Your source code is never stored. We use end-to-end encryption for all data in transit and are SOC 2 Type II certified. Enterprise customers can request on-premises deployment options.",
  },
]

interface FAQItemProps {
  question: string
  answer: string
  isOpen: boolean
  onToggle: () => void
}

const FAQItem = ({ question, answer, isOpen, onToggle }: FAQItemProps) => {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault()
    onToggle()
  }
  return (
    <div
      className="w-full bg-[rgba(231,236,235,0.08)] shadow-[0px_2px_4px_rgba(0,0,0,0.16)] overflow-hidden rounded-[10px] outline outline-1 outline-border outline-offset-[-1px] transition-all duration-500 ease-out cursor-pointer"
      onClick={handleClick}
    >
      <div className="w-full px-5 py-[18px] pr-4 flex justify-between items-center gap-5 text-left transition-all duration-300 ease-out">
        <div className="flex-1 text-foreground text-base font-medium leading-6 break-words">{question}</div>
        <div className="flex justify-center items-center">
          <ChevronDown
            className={`w-6 h-6 text-muted-foreground transition-all duration-500 ease-out ${isOpen ? "rotate-180 scale-110" : "rotate-0 scale-100"}`}
          />
        </div>
      </div>
      <div
        className={`overflow-hidden transition-all duration-500 ease-out ${isOpen ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"}`}
        style={{ transitionProperty: "max-height, opacity, padding", transitionTimingFunction: "cubic-bezier(0.4, 0, 0.2, 1)" }}
      >
        <div className={`px-5 transition-all duration-500 ease-out ${isOpen ? "pb-[18px] pt-2 translate-y-0" : "pb-0 pt-0 -translate-y-2"}`}>
          <div className="text-foreground/80 text-sm font-normal leading-6 break-words">{answer}</div>
        </div>
      </div>
    </div>
  )
}

export function FAQSection() {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set())
  const toggleItem = (index: number) => {
    const newOpenItems = new Set(openItems)
    if (newOpenItems.has(index)) { newOpenItems.delete(index) } else { newOpenItems.add(index) }
    setOpenItems(newOpenItems)
  }
  return (
    <section className="w-full pt-[66px] pb-20 md:pb-40 px-5 relative flex flex-col justify-center items-center">
      <div className="w-[300px] h-[500px] absolute top-[150px] left-1/2 -translate-x-1/2 origin-top-left rotate-[-33.39deg] bg-primary/10 blur-[100px] z-0" />
      <div className="self-stretch pt-8 pb-8 md:pt-14 md:pb-14 flex flex-col justify-center items-center gap-2 relative z-10">
        <div className="flex flex-col justify-start items-center gap-4">
          <h2 className="w-full max-w-[435px] text-center text-foreground text-4xl font-semibold leading-10 break-words">
            Frequently Asked Questions
          </h2>
          <p className="self-stretch text-center text-muted-foreground text-sm font-medium leading-[18.20px] break-words">
            Everything you need to know about Argus and how it can transform your code review workflow
          </p>
        </div>
      </div>
      <div className="w-full max-w-[600px] pt-0.5 pb-10 flex flex-col justify-start items-start gap-4 relative z-10">
        {faqData.map((faq, index) => (
          <FAQItem key={index} {...faq} isOpen={openItems.has(index)} onToggle={() => toggleItem(index)} />
        ))}
      </div>
    </section>
  )
}
