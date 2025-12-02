import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { adminService } from "@/services/api/admin"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export const AdminSettings: React.FC = () => {
  const queryClient = useQueryClient()
  const [promptValue, setPromptValue] = useState("")

  // Fetch all configs
  const { data: configs, isLoading } = useQuery({
    queryKey: ["adminConfigs"],
    queryFn: () => adminService.getAllConfigs(),
  })

  // Find ai_report_prompt config
  const promptConfig = configs?.find((c) => c.key === "ai_report_prompt")

  // Initialize prompt value when config loads
  React.useEffect(() => {
    if (promptConfig && promptValue === "") {
      setPromptValue(promptConfig.value)
    }
  }, [promptConfig, promptValue])

  // Update config mutation
  const updateMutation = useMutation({
    mutationFn: (value: string) =>
      adminService.updateConfig("ai_report_prompt", {
        value,
        description: promptConfig?.description || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      toast.success("Configuration saved successfully!")
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to save configuration"
      )
    },
  })

  const handleSave = () => {
    if (!promptConfig) {
      toast.error("Configuration key not found")
      return
    }
    updateMutation.mutate(promptValue)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Settings</h1>
          <p className="text-muted-foreground">Manage system configurations</p>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin Settings</h1>
        <p className="text-muted-foreground">Manage system configurations</p>
      </div>

      {/* System Configs List */}
      <Card>
        <CardHeader>
          <CardTitle>System Configurations</CardTitle>
          <CardDescription>
            All system configuration keys and values
          </CardDescription>
        </CardHeader>
        <CardContent>
          {configs && configs.length > 0 ? (
            <div className="space-y-4">
              {configs.map((config: ConfigItem) => (
                <div
                  key={config.key}
                  className="flex items-start justify-between border-b border-border pb-4 last:border-0"
                >
                  <div className="flex-1">
                    <p className="font-medium">{config.key}</p>
                    {config.description && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {config.description}
                      </p>
                    )}
                    <p className="text-sm text-muted-foreground mt-2 break-all">
                      {config.value.length > 100
                        ? `${config.value.substring(0, 100)}...`
                        : config.value}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No configurations found</p>
          )}
        </CardContent>
      </Card>

      {/* Prompt Editor */}
      <Card>
        <CardHeader>
          <CardTitle>AI Report Prompt Editor</CardTitle>
          <CardDescription>
            Edit the prompt template used for AI report generation
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="prompt">Prompt Template</Label>
            <Textarea
              id="prompt"
              value={promptValue}
              onChange={(e) => setPromptValue(e.target.value)}
              className="mt-2 min-h-[300px] font-mono text-sm"
              placeholder="Enter AI report prompt template..."
            />
            {promptConfig?.description && (
              <p className="text-sm text-muted-foreground mt-2">
                {promptConfig.description}
              </p>
            )}
          </div>
          <Button
            onClick={handleSave}
            disabled={updateMutation.isPending || !promptConfig}
          >
            <Save className="h-4 w-4 mr-2" />
            {updateMutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

