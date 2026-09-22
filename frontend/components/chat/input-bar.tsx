"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Square, CornerDownLeft, Mic, MicOff, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";

interface InputBarProps {
  onSendMessage: (message: string) => void;
  onStopStreaming?: () => void;
  isStreaming: boolean;
  selectedBrand: string;
}

export function InputBar({
  onSendMessage,
  onStopStreaming,
  isStreaming,
  selectedBrand,
}: InputBarProps) {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [voiceLang, setVoiceLang] = useState<"en-US" | "ar-EG">("en-US");
  const [speechSupported, setSpeechSupported] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (!isStreaming) {
      textareaRef.current?.focus();
    }
  }, [isStreaming]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechSupported(true);
      }
    }
  }, []);

  const handleToggleVoice = () => {
    if (!speechSupported) {
      alert("Speech recognition is not supported in this browser. Please try Chrome or Edge.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = voiceLang;
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInput((prev) => (prev.trim() ? `${prev.trim()} ${transcript}` : transcript));
          if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(
              textareaRef.current.scrollHeight,
              180
            )}px`;
          }
        }
        setIsListening(false);
      };

      recognition.onerror = (err: any) => {
        console.warn("Speech recognition error:", err);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e) {
      console.error("Failed to start speech recognition:", e);
      setIsListening(false);
    }
  };

  const toggleVoiceLang = () => {
    setVoiceLang((prev) => (prev === "en-US" ? "ar-EG" : "en-US"));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (isStreaming) {
      onStopStreaming?.();
      return;
    }
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 lg:px-8 pb-4 pt-2">
      <div className="relative flex flex-col rounded-2xl border border-border/80 bg-card shadow-lg focus-within:border-emerald-500/60 focus-within:ring-2 focus-within:ring-emerald-500/10 transition-all">
        {/* Input Area */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={
            isListening
              ? `Listening in ${voiceLang === "en-US" ? "English" : "Arabic"}... Speak now`
              : `Ask about ${selectedBrand === "All Brands" ? "any product, tracking, or order" : selectedBrand}...`
          }
          rows={1}
          className="w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-44"
        />

        {/* Action Controls Toolbar */}
        <div className="flex items-center justify-between px-3 py-2 border-t border-border/30 bg-muted/10">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="hidden sm:inline-flex items-center gap-1 font-mono">
              <CornerDownLeft className="w-3 h-3 text-muted-foreground/80" />
              Enter to send
            </span>
            <span className="hidden sm:inline-block text-border">•</span>
            <span className="hidden sm:inline font-mono">Shift + Enter for newline</span>
          </div>

          <div className="flex items-center gap-2">
            {/* Voice Language Toggle */}
            {speechSupported && (
              <button
                type="button"
                onClick={toggleVoiceLang}
                title={`Switch speech recognition language (Currently: ${voiceLang === "en-US" ? "English" : "Arabic"})`}
                className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                {voiceLang === "en-US" ? "EN" : "AR"}
              </button>
            )}

            {/* Speech-to-Text Microphone Button (Milestone 7) */}
            {speechSupported && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleToggleVoice}
                disabled={isStreaming}
                className={`h-8 w-8 p-0 rounded-xl transition-all ${
                  isListening
                    ? "bg-rose-500/20 text-rose-500 border border-rose-500/50 animate-pulse"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
                title={isListening ? "Listening... Click to stop" : "Voice input (Speech to Text)"}
              >
                {isListening ? (
                  <MicOff className="w-4 h-4" />
                ) : (
                  <Mic className="w-4 h-4" />
                )}
              </Button>
            )}

            {isStreaming ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={onStopStreaming}
                className="h-8 px-3 rounded-xl text-xs gap-1.5 font-medium"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Stop</span>
              </Button>
            ) : (
              <Button
                type="button"
                variant="default"
                size="sm"
                onClick={handleSubmit}
                disabled={!input.trim()}
                className="h-8 px-3 rounded-xl text-xs gap-1.5 font-medium bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
