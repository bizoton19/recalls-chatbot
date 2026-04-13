"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import type { Components } from "react-markdown";

const components: Components = {
  a({ href, children, ...props }) {
    const external = href?.startsWith("http");
    return (
      <a
        href={href}
        {...props}
        target={external ? "_blank" : undefined}
        rel={external ? "noopener noreferrer" : undefined}
      >
        {children}
      </a>
    );
  },
};

type Props = {
  children: string;
  className?: string;
};

/**
 * Renders assistant chat content as safe GitHub-flavored Markdown (bold, lists, links).
 */
export function ChatMarkdown({ children, className }: Props) {
  return (
    <div className={className ?? "chat-markdown"}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
