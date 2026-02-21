import * as React from "react"
import { useState, useCallback, useRef, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Save, RotateCcw, Plus, Edit2, Trash2, Database } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { adminService } from "@/services/api/admin"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

const AI_REPORT_MODELS_KEY = "ai_report_models_json"
const AI_IMAGE_MODELS_KEY = "ai_image_models_json"

interface AIModel {
  id: string
  provider: string
  label: string
  enabled?: boolean // Whether this model is available for users (default: true)
}

function parseModelsJson(jsonStr: string): { valid: boolean; models?: AIModel[]; error?: string } {
  if (!jsonStr.trim()) return { valid: true, models: [] }
  try {
    const arr = JSON.parse(jsonStr)
    if (!Array.isArray(arr)) return { valid: false, error: "Must be a JSON array" }
    const models: AIModel[] = []
    for (let i = 0; i < arr.length; i++) {
      const item = arr[i]
      if (!item || typeof item !== "object" || !item.id) {
        return { valid: false, error: `Item ${i + 1}: must have "id"` }
      }
      models.push({
        id: String(item.id),
        provider: String(item.provider || "zenmux"),
        label: String(item.label || item.id),
        enabled: item.enabled !== undefined ? Boolean(item.enabled) : true, // Default to enabled
      })
    }
    return { valid: true, models }
  } catch (e) {
    return { valid: false, error: (e as Error).message }
  }
}

function stringifyModels(models: AIModel[]): string {
  return JSON.stringify(models, null, 2)
}

export const AdminSettings: React.FC = () => {
  const queryClient = useQueryClient()

  // Feature flags state
  const [anomalyRadarEnabled, setAnomalyRadarEnabled] = useState(false)
  const [dailyPicksEnabled, setDailyPicksEnabled] = useState(false)
  const featureFlagsDebounceRef = useRef<ReturnType<typeof setTimeout>>()

  // AI Models state
  const [reportModels, setReportModels] = useState<AIModel[]>([])
  const [imageModels, setImageModels] = useState<AIModel[]>([])
  const [editingModel, setEditingModel] = useState<{ type: "report" | "image"; index?: number; model?: AIModel } | null>(null)
  const [newModelForm, setNewModelForm] = useState<AIModel>({ id: "", provider: "zenmux", label: "", enabled: true })

  // Fetch feature flags
  const { data: featureFlags, isLoading: isLoadingFlags } = useQuery({
    queryKey: ["adminFeatureFlags"],
    queryFn: () => adminService.getFeatureFlags(),
  })

  // Sync feature flags to state
  useEffect(() => {
    if (featureFlags) {
      setAnomalyRadarEnabled(featureFlags.anomaly_radar_enabled)
      setDailyPicksEnabled(featureFlags.daily_picks_enabled)
    }
  }, [featureFlags])

  // Fetch configs (for AI models)
  const { data: configs, isLoading: isLoadingConfigs } = useQuery({
    queryKey: ["adminConfigs"],
    queryFn: () => adminService.getAllConfigs(),
  })

  // Built-in defaults
  const { data: aiModelsDefault } = useQuery({
    queryKey: ["adminAIModelsDefault"],
    queryFn: () => adminService.getAIModelsDefault(),
  })

  // Sync AI models from configs
  useEffect(() => {
    if (!configs) return
    const reportConfig = configs.find((c) => c.key === AI_REPORT_MODELS_KEY)
    const imageConfig = configs.find((c) => c.key === AI_IMAGE_MODELS_KEY)

    if (reportConfig?.value) {
      const parsed = parseModelsJson(reportConfig.value)
      if (parsed.valid && parsed.models) {
        setReportModels(parsed.models)
      }
    } else if (aiModelsDefault) {
      setReportModels(aiModelsDefault.report_models)
    }

    if (imageConfig?.value) {
      const parsed = parseModelsJson(imageConfig.value)
      if (parsed.valid && parsed.models) {
        setImageModels(parsed.models)
      }
    } else if (aiModelsDefault) {
      setImageModels(aiModelsDefault.image_models)
    }
  }, [configs, aiModelsDefault])

  // Feature flags mutation (with debounce)
  const updateFeatureFlagsMutation = useMutation({
    mutationFn: (request: { anomaly_radar_enabled?: boolean; daily_picks_enabled?: boolean }) =>
      adminService.updateFeatureFlags(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminFeatureFlags"] })
      queryClient.invalidateQueries({ queryKey: ["featureFlags"] }) // Public endpoint cache
      toast.success("Feature flags updated")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to update")
    },
  })

  const handleFeatureFlagChange = useCallback((flag: "anomaly_radar" | "daily_picks", value: boolean) => {
    if (flag === "anomaly_radar") {
      setAnomalyRadarEnabled(value)
    } else {
      setDailyPicksEnabled(value)
    }

    // Debounce API call
    if (featureFlagsDebounceRef.current) {
      clearTimeout(featureFlagsDebounceRef.current)
    }
    featureFlagsDebounceRef.current = setTimeout(() => {
      updateFeatureFlagsMutation.mutate({
        [flag === "anomaly_radar" ? "anomaly_radar_enabled" : "daily_picks_enabled"]: value,
      })
    }, 500)
  }, [updateFeatureFlagsMutation])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (featureFlagsDebounceRef.current) {
        clearTimeout(featureFlagsDebounceRef.current)
      }
    }
  }, [])

  // AI Models mutations
  const saveReportModelsMutation = useMutation({
    mutationFn: (models: AIModel[]) =>
      adminService.updateConfig(AI_REPORT_MODELS_KEY, {
        value: stringifyModels(models),
        description: "JSON array of { id, provider, label } for report model list",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      toast.success("Report models saved")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save")
    },
  })

  const saveImageModelsMutation = useMutation({
    mutationFn: (models: AIModel[]) =>
      adminService.updateConfig(AI_IMAGE_MODELS_KEY, {
        value: stringifyModels(models),
        description: "JSON array of { id, provider, label } for image model list",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      toast.success("Image models saved")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to save")
    },
  })

  const deleteReportModelsMutation = useMutation({
    mutationFn: () => adminService.deleteConfig(AI_REPORT_MODELS_KEY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      if (aiModelsDefault) {
        setReportModels(aiModelsDefault.report_models)
      }
      toast.success("Report models reset to default")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to reset")
    },
  })

  const deleteImageModelsMutation = useMutation({
    mutationFn: () => adminService.deleteConfig(AI_IMAGE_MODELS_KEY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminConfigs"] })
      if (aiModelsDefault) {
        setImageModels(aiModelsDefault.image_models)
      }
      toast.success("Image models reset to default")
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to reset")
    },
  })

  // Data clear: confirm dialog state ("daily_picks" | "anomalies" | "all" | null)
  const [clearConfirmDialog, setClearConfirmDialog] = useState<"daily_picks" | "anomalies" | "all" | null>(null)

  const clearDailyPicksMutation = useMutation({
    mutationFn: () => adminService.clearDailyPicks(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["dailyPicks"] })
      setClearConfirmDialog(null)
      toast.success(`Cleared ${data.deleted} Daily Picks record(s)`)
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to clear Daily Picks")
    },
  })

  const clearAnomaliesMutation = useMutation({
    mutationFn: () => adminService.clearAnomalies(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["anomalies"] })
      setClearConfirmDialog(null)
      toast.success(`Cleared ${data.deleted} Anomaly Radar record(s)`)
    },
    onError: (error: unknown) => {
      toast.error((error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to clear Anomaly Radar")
    },
  })

  const clearAllMutation = useMutation({
    mutationFn: async () => {
      const [dailyResult, anomalyResult] = await Promise.all([
        adminService.clearDailyPicks(),
        adminService.clearAnomalies(),
      ])
      return { dailyResult, anomalyResult }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["dailyPicks"] })
      queryClient.invalidateQueries({ queryKey: ["anomalies"] })
      setClearConfirmDialog(null)
      toast.success(
        `Cleared ${data.dailyResult.deleted} Daily Picks and ${data.anomalyResult.deleted} Anomaly Radar records`
      )
    },
    onError: (error: unknown) => {
      toast.error(
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          "Failed to clear data"
      )
    },
  })

  const confirmClear = () => {
    if (clearConfirmDialog === "daily_picks") {
      clearDailyPicksMutation.mutate()
    } else if (clearConfirmDialog === "anomalies") {
      clearAnomaliesMutation.mutate()
    } else if (clearConfirmDialog === "all") {
      clearAllMutation.mutate()
    }
  }

  const isClearPending =
    clearDailyPicksMutation.isPending || clearAnomaliesMutation.isPending || clearAllMutation.isPending

  const handleSaveModels = (type: "report" | "image") => {
    if (type === "report") {
      saveReportModelsMutation.mutate(reportModels)
    } else {
      saveImageModelsMutation.mutate(imageModels)
    }
  }

  const handleAddModel = (type: "report" | "image") => {
    setNewModelForm({ id: "", provider: "zenmux", label: "", enabled: true })
    setEditingModel({ type })
  }

  const handleEditModel = (type: "report" | "image", index: number) => {
    const models = type === "report" ? reportModels : imageModels
    setNewModelForm({ ...models[index] })
    setEditingModel({ type, index })
  }

  const handleDeleteModel = (type: "report" | "image", index: number) => {
    if (type === "report") {
      const newModels = reportModels.filter((_, i) => i !== index)
      setReportModels(newModels)
      saveReportModelsMutation.mutate(newModels)
    } else {
      const newModels = imageModels.filter((_, i) => i !== index)
      setImageModels(newModels)
      saveImageModelsMutation.mutate(newModels)
    }
  }

  const handleSaveModelForm = () => {
    if (!editingModel) return
    if (!newModelForm.id.trim()) {
      toast.error("Model ID is required")
      return
    }
    if (!newModelForm.label.trim()) {
      toast.error("Model label is required")
      return
    }

    const models = editingModel.type === "report" ? [...reportModels] : [...imageModels]
    if (editingModel.index !== undefined) {
      models[editingModel.index] = { ...newModelForm }
    } else {
      models.push({ ...newModelForm })
    }

    if (editingModel.type === "report") {
      setReportModels(models)
      saveReportModelsMutation.mutate(models)
    } else {
      setImageModels(models)
      saveImageModelsMutation.mutate(models)
    }
    setEditingModel(null)
  }

  const isLoading = isLoadingFlags || isLoadingConfigs

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
          <p className="text-muted-foreground">Manage system feature flags and AI model configuration</p>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
        <p className="text-muted-foreground">Manage system feature flags and AI model configuration</p>
      </div>

      {/* Feature Flags */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Flags</CardTitle>
          <CardDescription>
            Control frontend feature display and backend task scheduling. Changes take effect immediately, no restart required.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="anomaly-radar" className="text-base font-medium">
                Anomaly Radar
              </Label>
              <p className="text-sm text-muted-foreground">
                When enabled, frontend displays Anomaly Radar feature, scheduler scans for anomalies every 5 minutes
              </p>
            </div>
            <Switch
              id="anomaly-radar"
              checked={anomalyRadarEnabled}
              onCheckedChange={(checked) => handleFeatureFlagChange("anomaly_radar", checked)}
              disabled={updateFeatureFlagsMutation.isPending}
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="daily-picks" className="text-base font-medium">
                Daily Picks
              </Label>
              <p className="text-sm text-muted-foreground">
                When enabled, frontend displays Daily Picks feature, scheduler generates daily picks at 8:30 EST
              </p>
            </div>
            <Switch
              id="daily-picks"
              checked={dailyPicksEnabled}
              onCheckedChange={(checked) => handleFeatureFlagChange("daily_picks", checked)}
              disabled={updateFeatureFlagsMutation.isPending}
            />
          </div>
          {updateFeatureFlagsMutation.isPending && (
            <p className="text-xs text-muted-foreground">Saving...</p>
          )}
        </CardContent>
      </Card>

      {/* Data Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Data Management
          </CardTitle>
          <CardDescription>
            One-click clear Daily Picks and Anomaly Radar data. This cannot be undone.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setClearConfirmDialog("daily_picks")}
            disabled={isClearPending}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Clear Daily Picks
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setClearConfirmDialog("anomalies")}
            disabled={isClearPending}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Clear Anomaly Radar
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setClearConfirmDialog("all")}
            disabled={isClearPending}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Clear All (Daily Picks + Radar)
          </Button>
        </CardContent>
      </Card>

      {/* Clear data confirmation dialog */}
      <Dialog open={clearConfirmDialog !== null} onOpenChange={(open) => !open && setClearConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear data?</DialogTitle>
            <DialogDescription>
              {clearConfirmDialog === "daily_picks" &&
                "This will permanently delete all Daily Picks records. This cannot be undone."}
              {clearConfirmDialog === "anomalies" &&
                "This will permanently delete all Anomaly Radar records. This cannot be undone."}
              {clearConfirmDialog === "all" &&
                "This will permanently delete all Daily Picks and Anomaly Radar records. This cannot be undone."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearConfirmDialog(null)} disabled={isClearPending}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmClear} disabled={isClearPending}>
              {isClearPending ? "Clearing..." : "Clear"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AI Report Models */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Report Models</CardTitle>
              <CardDescription>
                List of AI models available for user report generation. If left empty, built-in default list will be used.
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => deleteReportModelsMutation.mutate()}
                disabled={deleteReportModelsMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                Reset to Default
              </Button>
              <Button
                size="sm"
                onClick={() => handleSaveModels("report")}
                disabled={saveReportModelsMutation.isPending}
              >
                <Save className="h-4 w-4 mr-1" />
                {saveReportModelsMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button size="sm" onClick={() => handleAddModel("report")}>
                <Plus className="h-4 w-4 mr-1" />
                Add Model
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {reportModels.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[60px]">Enabled</TableHead>
                  <TableHead className="w-[200px]">Model ID</TableHead>
                  <TableHead className="w-[120px]">Provider</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead className="w-[100px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportModels.map((model, index) => (
                  <TableRow key={`${model.id}-${index}`}>
                    <TableCell>
                      <Switch
                        checked={model.enabled !== false}
                        onCheckedChange={(checked) => {
                          const updatedModels = [...reportModels]
                          updatedModels[index] = { ...updatedModels[index], enabled: checked }
                          setReportModels(updatedModels)
                          saveReportModelsMutation.mutate(updatedModels)
                        }}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-sm">{model.id}</TableCell>
                    <TableCell>{model.provider}</TableCell>
                    <TableCell>
                      <span className={model.enabled === false ? "text-muted-foreground line-through" : ""}>
                        {model.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditModel("report", index)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteModel("report", index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              No models configured. Built-in default list will be used. Click "Add Model" or "Reset to Default".
            </p>
          )}
        </CardContent>
      </Card>

      {/* AI Image Models */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Image Models</CardTitle>
              <CardDescription>
                List of AI models available for user image generation. If left empty, built-in default list will be used.
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => deleteImageModelsMutation.mutate()}
                disabled={deleteImageModelsMutation.isPending}
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                Reset to Default
              </Button>
              <Button
                size="sm"
                onClick={() => handleSaveModels("image")}
                disabled={saveImageModelsMutation.isPending}
              >
                <Save className="h-4 w-4 mr-1" />
                {saveImageModelsMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button size="sm" onClick={() => handleAddModel("image")}>
                <Plus className="h-4 w-4 mr-1" />
                Add Model
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {imageModels.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[60px]">Enabled</TableHead>
                  <TableHead className="w-[200px]">Model ID</TableHead>
                  <TableHead className="w-[120px]">Provider</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead className="w-[100px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {imageModels.map((model, index) => (
                  <TableRow key={`${model.id}-${index}`}>
                    <TableCell>
                      <Switch
                        checked={model.enabled !== false}
                        onCheckedChange={(checked) => {
                          const updatedModels = [...imageModels]
                          updatedModels[index] = { ...updatedModels[index], enabled: checked }
                          setImageModels(updatedModels)
                          saveImageModelsMutation.mutate(updatedModels)
                        }}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-sm">{model.id}</TableCell>
                    <TableCell>{model.provider}</TableCell>
                    <TableCell>
                      <span className={model.enabled === false ? "text-muted-foreground line-through" : ""}>
                        {model.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditModel("image", index)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteModel("image", index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground text-center py-8">
              No models configured. Built-in default list will be used. Click "Add Model" or "Reset to Default".
            </p>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Model Dialog */}
      <Dialog open={editingModel !== null} onOpenChange={(open) => !open && setEditingModel(null)}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {editingModel?.index !== undefined ? "Edit Model" : "Add Model"}
            </DialogTitle>
            <DialogDescription>
              {editingModel?.type === "report" ? "Report generation model" : "Image generation model"}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="model-id">Model ID *</Label>
              <Input
                id="model-id"
                value={newModelForm.id}
                onChange={(e) => setNewModelForm({ ...newModelForm, id: e.target.value })}
                placeholder="e.g., gemini-3-flash-preview or z-ai/glm-5"
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground">
                ZenMux model format: provider/model (e.g., z-ai/glm-5)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="model-provider">Provider</Label>
              <Select
                value={newModelForm.provider}
                onValueChange={(value) => setNewModelForm({ ...newModelForm, provider: value })}
              >
                <SelectTrigger id="model-provider">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gemini">Gemini</SelectItem>
                  <SelectItem value="zenmux">ZenMux</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="model-label">Label *</Label>
              <Input
                id="model-label"
                value={newModelForm.label}
                onChange={(e) => setNewModelForm({ ...newModelForm, label: e.target.value })}
                placeholder="e.g., Gemini 3 Flash"
              />
              <p className="text-xs text-muted-foreground">Model name displayed in user interface</p>
            </div>
            <div className="flex items-center justify-between pt-2">
              <div className="space-y-0.5">
                <Label htmlFor="model-enabled">Enabled</Label>
                <p className="text-xs text-muted-foreground">
                  When disabled, this model will not be available for users to select
                </p>
              </div>
              <Switch
                id="model-enabled"
                checked={newModelForm.enabled !== false}
                onCheckedChange={(checked) => setNewModelForm({ ...newModelForm, enabled: checked })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingModel(null)}>
              Cancel
            </Button>
            <Button onClick={handleSaveModelForm}>
              {editingModel?.index !== undefined ? "Save" : "Add"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
