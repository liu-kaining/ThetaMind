import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Save, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { adminService, ConfigItem } from "@/services/api/admin"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

const AI_REPORT_MODELS_KEY = "ai_report_models_json"
const AI_IMAGE_MODELS_KEY = "ai_image_models_json"

function parseModelsJson(jsonStr: string): { valid: boolean; error?: string } {
  if (!jsonStr.trim()) return { valid: true }
  try {
    const arr = JSON.parse(jsonStr)
    if (!Array.isArray(arr)) return { valid: false, error: "Must be a JSON array" }
    for (let i = 0; i < arr.length; i++) {
      if (!arr[i] || typeof arr[i] !== "object" || !arr[i].id) {
        return { valid: false, error: `Item ${i + 1}: must have "id"` }
      }
    }
    return { valid: true }
  } catch (e) {
    return { valid: false, error: (e as Error).message }
  }
}

export const AdminSettings: React.FC = () => {
  const queryClient = useQueryClient()
  const [promptValue, setPromptValue] = useState("")
  const [reportModelsJson, setReportModelsJson] = useState("")
  const [imageModelsJson, setImageModelsJson] = useState("")

  // Fetch all configs
  const { data: configs, isLoading } = useQuery({
    queryKey: ["adminConfigs"],
    queryFn: () => adminService.getAllConfigs(),
  })

  // Built-in defaults (for reset and reference)
  const { data: aiModelsDefault } = useQuery({
    queryKey: ["adminAIModelsDefault"],
    queryFn: () => adminService.getAIModelsDefault(),
  })

  // Find ai_report_prompt config
  const promptConfig = configs?.find((c) => c.key === "ai_report_prompt")

  // Initialize prompt value when config loads
  React.useEffect(() => {
    if (promptConfig && promptValue === "") {
      setPromptValue(promptConfig.value)
    }
  }, [promptConfig, promptValue])

  // Sync report/image model JSON from configs (and after reset)
  React.useEffect(() => {
    if (!configs) return
    const reportConfig = configs.find((c) => c.key === AI_REPORT_MODELS_KEY)
    const imageConfig = configs.find((c) => c.key === AI_IMAGE_MODELS_KEY)
    setReportModelsJson(reportConfig?.value ?? "")
    setImageModelsJson(imageConfig?.value ?? "")
  }, [configs])

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

  // Save report models
  const saveReportModelsMutation = useMutation({
    mutationFn: (value: string) =>
      adminService.updateConfig(AI_REPORT_MODELS_KEY, {
        value,
        description: "JSON array of { id, provider, label } for report model list",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      toast.success("Report models saved. Frontend will use new list after refresh.")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save")
    },
  })

  const saveImageModelsMutation = useMutation({
    mutationFn: (value: string) =>
      adminService.updateConfig(AI_IMAGE_MODELS_KEY, {
        value,
        description: "JSON array of { id, provider, label } for image model list",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      toast.success("Image models saved.")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save")
    },
  })

  const deleteReportModelsMutation = useMutation({
    mutationFn: () => adminService.deleteConfig(AI_REPORT_MODELS_KEY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      setReportModelsJson("")
      toast.success("Report models reset to built-in default.")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to reset")
    },
  })

  const deleteImageModelsMutation = useMutation({
    mutationFn: () => adminService.deleteConfig(AI_IMAGE_MODELS_KEY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      setImageModelsJson("")
      toast.success("Image models reset to built-in default.")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to reset")
    },
  })

  const handleSaveReportModels = () => {
    const { valid, error } = parseModelsJson(reportModelsJson)
    if (!valid) {
      toast.error(error ?? "Invalid JSON")
      return
    }
    saveReportModelsMutation.mutate(reportModelsJson.trim() || "[]")
  }

  const handleSaveImageModels = () => {
    const { valid, error } = parseModelsJson(imageModelsJson)
    if (!valid) {
      toast.error(error ?? "Invalid JSON")
      return
    }
    saveImageModelsMutation.mutate(imageModelsJson.trim() || "[]")
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

      {/* AI Model Lists (report + image) */}
      <Card>
        <CardHeader>
          <CardTitle>AI 模型列表</CardTitle>
          <CardDescription>
            报告与图片生成可选模型。留空则使用内置默认列表；修改后保存到数据库，无需改 .env 或重启。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>报告模型 (ai_report_models_json)</Label>
            <Textarea
              value={reportModelsJson}
              onChange={(e) => setReportModelsJson(e.target.value)}
              className="min-h-[180px] font-mono text-sm"
              placeholder='[{"id":"gemini-3-flash-preview","provider":"gemini","label":"Gemini 3 Flash"}, ...]'
            />
            <p className="text-xs text-muted-foreground">
              JSON 数组，每项需含 id, provider, label。空则使用内置默认（含 Gemini / ZenMux 多模型）。
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleSaveReportModels}
                disabled={saveReportModelsMutation.isPending}
              >
                <Save className="h-4 w-4 mr-1" />
                {saveReportModelsMutation.isPending ? "保存中…" : "保存"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => deleteReportModelsMutation.mutate()}
                disabled={deleteReportModelsMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                恢复默认
              </Button>
            </div>
          </div>
          <div className="space-y-2">
            <Label>图片模型 (ai_image_models_json)</Label>
            <Textarea
              value={imageModelsJson}
              onChange={(e) => setImageModelsJson(e.target.value)}
              className="min-h-[100px] font-mono text-sm"
              placeholder='[{"id":"google/gemini-3-pro-image-preview","provider":"zenmux","label":"Gemini 3 Pro Image"}, ...]'
            />
            <p className="text-xs text-muted-foreground">
              JSON 数组，每项需含 id, provider, label。空则使用内置默认。
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleSaveImageModels}
                disabled={saveImageModelsMutation.isPending}
              >
                <Save className="h-4 w-4 mr-1" />
                {saveImageModelsMutation.isPending ? "保存中…" : "保存"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => deleteImageModelsMutation.mutate()}
                disabled={deleteImageModelsMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                恢复默认
              </Button>
            </div>
          </div>
          {aiModelsDefault && (
            <p className="text-xs text-muted-foreground border-t pt-2">
              当前内置默认：报告 {aiModelsDefault.report_models.length} 个，图片 {aiModelsDefault.image_models.length} 个。
            </p>
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

