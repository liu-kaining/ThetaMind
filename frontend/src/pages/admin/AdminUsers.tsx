import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Search, Edit, Trash2, ShieldCheck, Crown, User as UserIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
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
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { adminService, UserResponse, UserUpdateRequest, UsersListResponse } from "@/services/api/admin"
import { toast } from "sonner"
import { format } from "date-fns"
import { AdminRoute } from "@/components/auth/AdminRoute"
import { useAuth } from "@/features/auth/AuthProvider"

// Helper function to extract error message from various error formats
function getErrorMessage(error: any): string {
  if (!error) return "An unknown error occurred"
  
  // Handle FastAPI validation errors (array of error objects)
  if (error?.response?.data?.detail) {
    const detail = error.response.data.detail
    if (Array.isArray(detail)) {
      // Pydantic validation errors: [{type, loc, msg, ...}, ...]
      return detail.map((err: any) => {
        const field = err.loc?.join(".") || "field"
        return `${field}: ${err.msg || "Invalid value"}`
      }).join(", ")
    }
    if (typeof detail === "string") {
      return detail
    }
    if (typeof detail === "object") {
      // Try to extract a meaningful message
      return detail.msg || detail.message || "Validation error"
    }
  }
  
  // Fallback to error message
  if (typeof error.message === "string") {
    return error.message
  }
  
  return "An unknown error occurred"
}

export const AdminUsers: React.FC = () => {
  const { user: currentUser } = useAuth()
  const [searchQuery, setSearchQuery] = React.useState("")
  const [page, setPage] = React.useState(0)
  const [selectedUser, setSelectedUser] = React.useState<UserResponse | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = React.useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false)
  const [editForm, setEditForm] = React.useState<UserUpdateRequest>({})

  const limit = 50
  const queryClient = useQueryClient()
  const [debouncedSearchQuery, setDebouncedSearchQuery] = React.useState("")
  const prevSearchRef = React.useRef("")

  // Debounce search query (reduced delay for better UX, avoid jitter)
  React.useEffect(() => {
    const timer = setTimeout(() => {
      const trimmedQuery = searchQuery.trim()
      // Only update if search query actually changed (avoid unnecessary resets)
      if (trimmedQuery !== prevSearchRef.current) {
        prevSearchRef.current = trimmedQuery
        setDebouncedSearchQuery(trimmedQuery)
        // Reset page only when search query actually changes (not on every keystroke)
        setPage(0)
      }
    }, 200) // Reduced from 300ms to 200ms for faster response
    return () => clearTimeout(timer)
  }, [searchQuery]) // Only depend on searchQuery to avoid loops

  // Fetch users with placeholderData to avoid jitter during search
  const { data: usersData, isLoading, error } = useQuery({
    queryKey: ["admin", "users", page, debouncedSearchQuery],
    queryFn: () => adminService.listUsers(limit, page * limit, debouncedSearchQuery || undefined),
    placeholderData: (previousData: UsersListResponse | undefined) => previousData, // Keep previous data while loading new data to avoid jitter (React Query v5)
    staleTime: 1000, // Consider data fresh for 1 second to reduce unnecessary refetches
  })
  
  // Safely extract data with type checking (handle both new format and potential old format)
  const users = React.useMemo(() => {
    if (!usersData) return []
    // Check if it's the new format (object with users array)
    if (typeof usersData === 'object' && 'users' in usersData && Array.isArray(usersData.users)) {
      return usersData.users
    }
    // Fallback: if it's an array (old format), return it directly
    if (Array.isArray(usersData)) {
      return usersData
    }
    return []
  }, [usersData])
  
  const total = React.useMemo(() => {
    if (!usersData) return 0
    // Check if it's the new format (object with total)
    if (typeof usersData === 'object' && 'total' in usersData && typeof usersData.total === 'number') {
      return usersData.total
    }
    // Fallback: if it's an array (old format), return array length
    if (Array.isArray(usersData)) {
      return usersData.length
    }
    return 0
  }, [usersData])
  
  const totalPages = limit > 0 ? Math.ceil(total / limit) : 0
  
  // Check if selected user is current user
  const isCurrentUser = selectedUser?.id === currentUser?.id

  // Calculate statistics (only from current page - note: this is approximate)
  const stats = React.useMemo(() => {
    if (!usersData || !Array.isArray(users)) return null
    // For accurate stats, we'd need a separate endpoint, but for now use current page data
    const totalUsers = typeof total === 'number' && !isNaN(total) ? total : 0
    const proUsers = users.filter((u) => u && typeof u === 'object' && Boolean(u.is_pro)).length
    const adminUsers = users.filter((u) => u && typeof u === 'object' && Boolean(u.is_superuser)).length
    const totalStrategies = users.reduce((sum, u) => {
      if (u && typeof u === 'object' && typeof u.strategies_count === 'number') {
        return sum + u.strategies_count
      }
      return sum
    }, 0)
    const totalReports = users.reduce((sum, u) => {
      if (u && typeof u === 'object' && typeof u.ai_reports_count === 'number') {
        return sum + u.ai_reports_count
      }
      return sum
    }, 0)
    return {
      totalUsers: Math.max(0, totalUsers),
      proUsers: Math.max(0, proUsers),
      adminUsers: Math.max(0, adminUsers),
      totalStrategies: Math.max(0, totalStrategies),
      totalReports: Math.max(0, totalReports),
    }
  }, [usersData, users, total])

  // Update user mutation
  const updateUserMutation = useMutation({
    mutationFn: (data: { userId: string; request: UserUpdateRequest }) =>
      adminService.updateUser(data.userId, data.request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
      setIsEditDialogOpen(false)
      setSelectedUser(null)
      setEditForm({}) // Reset form
      toast.success("User updated successfully")
    },
    onError: (error: any) => {
      const errorMessage = getErrorMessage(error) || "Failed to update user"
      toast.error(errorMessage)
    },
  })

  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => adminService.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
      setIsDeleteDialogOpen(false)
      setSelectedUser(null)
      toast.success("User deleted successfully")
    },
    onError: (error: any) => {
      const errorMessage = getErrorMessage(error) || "Failed to delete user"
      toast.error(errorMessage)
    },
  })

  const handleEdit = (user: UserResponse) => {
    setSelectedUser(user)
    setEditForm({
      is_pro: Boolean(user.is_pro),
      is_superuser: Boolean(user.is_superuser),
      daily_ai_usage: user.daily_ai_usage ?? 0,
      plan_expiry_date: user.plan_expiry_date || null,
    })
    setIsEditDialogOpen(true)
  }

  const handleDelete = (user: UserResponse) => {
    setSelectedUser(user)
    setIsDeleteDialogOpen(true)
  }

  const handleSaveEdit = () => {
    if (!selectedUser) return
    
    // Build request with only defined fields
    const request: UserUpdateRequest = {}
    
    // Only include fields that are explicitly set
    if (editForm.is_pro !== undefined) {
      request.is_pro = Boolean(editForm.is_pro)
    }
    if (editForm.is_superuser !== undefined) {
      request.is_superuser = Boolean(editForm.is_superuser)
    }
    if (editForm.daily_ai_usage !== undefined) {
      request.daily_ai_usage = editForm.daily_ai_usage
    }
    
    // Convert date string (yyyy-MM-dd) to ISO datetime string for backend
    // Backend expects datetime in ISO format (e.g., "2025-12-31T00:00:00Z")
    if (editForm.plan_expiry_date !== undefined && editForm.plan_expiry_date !== null) {
      const dateStr = typeof editForm.plan_expiry_date === 'string' 
        ? editForm.plan_expiry_date.trim() 
        : String(editForm.plan_expiry_date)
      if (dateStr) {
        // If it's already in ISO format, use it; otherwise add time
        request.plan_expiry_date = dateStr.includes('T') 
          ? dateStr 
          : `${dateStr}T00:00:00Z`
      } else {
        request.plan_expiry_date = null
      }
    } else if (editForm.plan_expiry_date === null) {
      request.plan_expiry_date = null
    }
    
    updateUserMutation.mutate({
      userId: selectedUser.id,
      request,
    })
  }

  const handleConfirmDelete = () => {
    if (!selectedUser) return
    deleteUserMutation.mutate(selectedUser.id)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // Search is debounced, so just reset page
    setPage(0)
  }

  const handleSearchInputChange = (value: string) => {
    setSearchQuery(value)
    // Page reset happens in debounce effect
  }

  return (
    <AdminRoute>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">
            Manage all users, their permissions, and subscriptions
          </p>
        </div>

        {/* Statistics Cards */}
        {stats && (
          <div className="grid gap-4 md:grid-cols-5">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats.totalUsers}</div>
                <div className="text-xs text-muted-foreground">Total Users</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-purple-600">{stats.proUsers}</div>
                <div className="text-xs text-muted-foreground">Pro Users</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-red-600">{stats.adminUsers}</div>
                <div className="text-xs text-muted-foreground">Admins</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats.totalStrategies}</div>
                <div className="text-xs text-muted-foreground">Total Strategies</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold">{stats.totalReports}</div>
                <div className="text-xs text-muted-foreground">Total Reports</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Search */}
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by email... (auto-searches as you type)"
                  value={searchQuery}
                  onChange={(e) => handleSearchInputChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      handleSearch(e)
                    }
                  }}
                  className="pl-9"
                />
              </div>
              {searchQuery && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setSearchQuery("")
                    setDebouncedSearchQuery("")
                    setPage(0)
                  }}
                >
                  Clear
                </Button>
              )}
            </form>
            {debouncedSearchQuery && (
              <p className="text-xs text-muted-foreground mt-2">
                Searching for: "{debouncedSearchQuery}"
              </p>
            )}
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card>
          <CardHeader>
            <CardTitle>All Users</CardTitle>
            <CardDescription>
              {total.toLocaleString()} user{total !== 1 ? "s" : ""} found
              {debouncedSearchQuery ? ` (filtered by "${debouncedSearchQuery}")` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading users...</div>
            ) : error ? (
              <div className="text-center py-8 text-red-600">
                Error loading users: {getErrorMessage(error)}
              </div>
            ) : !users || users.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">No users found</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Usage</TableHead>
                      <TableHead>Strategies</TableHead>
                      <TableHead>Reports</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => {
                      // Ensure boolean values to prevent React error #31
                      const isSuperuser = Boolean(user?.is_superuser)
                      const isPro = Boolean(user?.is_pro)
                      
                      return (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">{user.email}</TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              {isSuperuser ? (
                                <Badge variant="destructive" className="gap-1">
                                  <ShieldCheck className="h-3 w-3" />
                                  Admin
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="gap-1">
                                  <UserIcon className="h-3 w-3" />
                                  User
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            {isPro ? (
                              <Badge className="gap-1 bg-gradient-to-r from-purple-500 to-pink-500">
                                <Crown className="h-3 w-3" />
                                Pro
                              </Badge>
                            ) : (
                              <Badge variant="outline">Free</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            <div className="flex items-center gap-2">
                              <span>{user.daily_ai_usage ?? 0}</span>
                              {(user.daily_ai_usage ?? 0) > 0 ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 text-xs"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleEdit(user)
                                    setEditForm((f) => ({ ...f, daily_ai_usage: 0 }))
                                  }}
                                  title="Reset usage"
                                >
                                  Reset
                                </Button>
                              ) : null}
                            </div>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {user.strategies_count ?? 0}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {user.ai_reports_count ?? 0}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {format(new Date(user.created_at), "MMM d, yyyy")}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleEdit(user)}
                                title="Edit user"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => handleDelete(user)}
                                title="Delete user"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Pagination */}
            {total > 0 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total.toLocaleString()} user{total !== 1 ? "s" : ""}
                  {totalPages > 1 ? ` (Page ${page + 1} of ${totalPages})` : ""}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0 || isLoading}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= totalPages - 1 || isLoading}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edit Dialog */}
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Edit User</DialogTitle>
              <DialogDescription>
                Update user permissions and subscription status
              </DialogDescription>
            </DialogHeader>
            {selectedUser && (
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Email</Label>
                  <div className="text-sm text-muted-foreground">{selectedUser.email}</div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="is_pro">Pro Subscription</Label>
                    <div className="text-xs text-muted-foreground">
                      Enable Pro features for this user
                    </div>
                  </div>
                  <Switch
                    id="is_pro"
                    checked={Boolean(editForm.is_pro)}
                    onCheckedChange={(checked) =>
                      setEditForm((f) => ({ ...f, is_pro: checked }))
                    }
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="is_superuser">Superuser (Admin)</Label>
                    <div className="text-xs text-muted-foreground">
                      Grant admin access to this user
                    </div>
                  </div>
                  <Switch
                    id="is_superuser"
                    checked={Boolean(editForm.is_superuser)}
                    onCheckedChange={(checked) =>
                      setEditForm((f) => ({ ...f, is_superuser: checked }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="daily_ai_usage">Daily AI Usage</Label>
                  <Input
                    id="daily_ai_usage"
                    type="number"
                    min="0"
                    value={editForm.daily_ai_usage ?? 0}
                    onChange={(e) =>
                      setEditForm((f) => ({
                        ...f,
                        daily_ai_usage: parseInt(e.target.value) || 0,
                      }))
                    }
                    className="max-w-[200px]"
                  />
                  <div className="text-xs text-muted-foreground">
                    Reset daily AI usage counter (0 to reset)
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="plan_expiry_date">Plan Expiry Date</Label>
                  <Input
                    id="plan_expiry_date"
                    type="date"
                    value={
                      editForm.plan_expiry_date
                        ? format(new Date(editForm.plan_expiry_date), "yyyy-MM-dd")
                        : ""
                    }
                    onChange={(e) =>
                      setEditForm((f) => ({
                        ...f,
                        plan_expiry_date: e.target.value || null,
                      }))
                    }
                    className="max-w-[200px]"
                  />
                </div>
              </div>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSaveEdit}
                disabled={updateUserMutation.isPending}
              >
                {updateUserMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete User</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete this user? This action cannot be undone and will
                delete all associated data (strategies, reports, etc.).
              </DialogDescription>
            </DialogHeader>
            {selectedUser && (
              <div className="py-4">
                <div className="text-sm font-medium">{selectedUser.email}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {selectedUser.strategies_count ?? 0} strategies • {selectedUser.ai_reports_count ?? 0}{" "}
                  reports
                </div>
              </div>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmDelete}
                disabled={deleteUserMutation.isPending || isCurrentUser}
              >
                {deleteUserMutation.isPending ? "Deleting..." : "Delete User"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </AdminRoute>
  )
}

