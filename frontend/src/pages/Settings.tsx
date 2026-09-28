/**
 * Settings page — Telegram configuration.
 * Shows current config status, form to set/update, test button.
 * All states explicit: loading → configured/not-configured → error.
 */

import { useState, useEffect, useCallback } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  CheckmarkCircle02Icon,
  Cancel01Icon,
  RefreshIcon,
} from "@hugeicons/core-free-icons"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import {
  getTelegramStatus,
  configureTelegram,
  testTelegram,
  clearTelegramConfig,
  type TelegramStatus,
} from "@/lib/watches-api"

export function Settings() {
  const [status, setStatus] = useState<TelegramStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")

  const [botToken, setBotToken] = useState("")
  const [chatId, setChatId] = useState("")
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [clearing, setClearing] = useState(false)

  const loadStatus = useCallback(async () => {
    setLoading(true)
    setLoadError("")
    try {
      const s = await getTelegramStatus()
      setStatus(s)
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : "Failed to load Telegram status")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  const handleSave = async () => {
    if (!botToken.trim() || !chatId.trim()) {
      toast.error("Both bot token and chat ID are required")
      return
    }
    setSaving(true)
    try {
      const result = await configureTelegram(botToken.trim(), chatId.trim())
      toast.success(`Connected to @${result.bot_username} (${result.bot_name})`)
      setBotToken("")
      setChatId("")
      await loadStatus()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to configure Telegram")
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      await testTelegram()
      toast.success("Test message sent! Check your Telegram.")
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Test failed")
    } finally {
      setTesting(false)
    }
  }

  const handleClear = async () => {
    setClearing(true)
    try {
      await clearTelegramConfig()
      toast.success("Telegram configuration removed")
      await loadStatus()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to clear config")
    } finally {
      setClearing(false)
    }
  }

  if (loading) {
    return (
      <div className="p-4 max-w-xl mx-auto space-y-3">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="p-4 max-w-xl mx-auto">
        <Card className="border-destructive">
          <CardContent className="pt-6 text-center">
            <HugeiconsIcon icon={Cancel01Icon} className="size-8 text-destructive mx-auto mb-2" />
            <p className="text-destructive font-medium">{loadError}</p>
            <Button className="mt-3" variant="outline" onClick={loadStatus}>
              <HugeiconsIcon icon={RefreshIcon} className="size-4 mr-1" /> Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-xl mx-auto">
      <h2 className="text-lg font-bold mb-4">Settings</h2>

      {/* Telegram status */}
      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-1.5">
            📱 Telegram Notifications
            {status?.configured ? (
              <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-4 text-green-500" />
            ) : (
              <HugeiconsIcon icon={Cancel01Icon} className="size-4 text-muted-foreground" />
            )}
          </CardTitle>
          <CardDescription className="text-xs">
            Receive deal alerts via Telegram when watch criteria are met.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {status?.configured ? (
            <>
              <div className="rounded-lg border border-green-300 bg-green-50 dark:bg-green-950/30 p-3 text-sm">
                <p className="font-medium text-green-700 dark:text-green-400">
                  ✅ Telegram configured
                </p>
                {status.chat_id && (
                  <p className="text-xs text-muted-foreground mt-0.5">Chat ID: {status.chat_id}</p>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={testing}
                  className="flex-1"
                >
                  {testing ? (
                    <Spinner className="size-4 mr-1" />
                  ) : (
                    <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-4 mr-1" />
                  )}
                  Send test message
                </Button>
                <Button
                  variant="ghost"
                  onClick={handleClear}
                  disabled={clearing}
                  className="text-destructive hover:text-destructive"
                >
                  {clearing ? <Spinner className="size-4" /> : "Remove"}
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="text-xs text-muted-foreground bg-muted rounded-lg p-3 space-y-1.5">
                <p>To set up Telegram alerts:</p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>
                    Message{" "}
                    <a
                      href="https://t.me/BotFather"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      @BotFather
                    </a>{" "}
                    to create a bot → get your <strong>Bot Token</strong>
                  </li>
                  <li>
                    Message{" "}
                    <a
                      href="https://t.me/userinfobot"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      @userinfobot
                    </a>{" "}
                    to get your <strong>Chat ID</strong>
                  </li>
                  <li>Enter both below and click Save</li>
                </ol>
              </div>

              <div className="space-y-2">
                <div>
                  <Label className="text-xs mb-1 block">Bot Token</Label>
                  <Input
                    value={botToken}
                    onChange={(e) => setBotToken(e.target.value)}
                    placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
                    className="text-sm font-mono"
                    type="password"
                  />
                </div>
                <div>
                  <Label className="text-xs mb-1 block">Chat ID</Label>
                  <Input
                    value={chatId}
                    onChange={(e) => setChatId(e.target.value)}
                    placeholder="e.g. 123456789"
                    className="text-sm"
                  />
                </div>
              </div>

              <Button
                className="w-full"
                onClick={handleSave}
                disabled={saving || !botToken.trim() || !chatId.trim()}
              >
                {saving ? <Spinner className="size-4 mr-1" /> : null}
                Save Telegram Config
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* App info */}
      <Card>
        <CardContent className="pt-4 text-xs text-muted-foreground space-y-1">
          <p className="font-medium text-foreground">About Cart Radar — Worth-It Layer</p>
          <p>Monitors products across Zepto, Swiggy Instamart, BigBasket, Blinkit, and more.</p>
          <p>Scan intervals: 5, 15, or 30 minutes. No continuous polling.</p>
        </CardContent>
      </Card>
    </div>
  )
}
