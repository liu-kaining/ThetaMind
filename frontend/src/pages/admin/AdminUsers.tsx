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
import { adminService, UserResponse, UserUpdateRequest } from "@/services/api/admin"
import { toast } from "sonner"
import { format } from "date-fns"
import { AdminRoute } from "@/components/auth/AdminRoute"
import { useAuth } from "@/features/auth/AuthProvider"

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

  // Fetch users
  const { data: users, isLoading } = useQuery({
    queryKey: ["admin", "users", page, searchQuery],
    queryFn: () => adminService.listUsers(limit, page * limit, searchQuery || undefined),
  })
  
  // Check if selected user is current user
  const isCurrentUser = selectedUser?.id === currentUser?.id

  // Calculate statistics
  const stats = React.useMemo(() => {
    if (!users) return null
    const totalUsers = users.length
    const proUsers = users.filter((u) => u.is_pro).length
    const adminUsers = users.filter((u) => u.is_superuser).length
    const totalStrategies = users.reduce((sum, u) => sum + u.strategies_count, 0)
    const totalReports = users.reduce((sum, u) => sum + u.ai_reports_count, 0)
    return {
      totalUsers,
      proUsers,
      adminUsers,
      totalStrategies,
      totalReports,
    }
  }, [users])

  // Update user mutation
  const updateUserMutation = useMutation({
    mutationFn: (data: { userId: string; request: UserUpdateRequest }) =>
      adminService.updateUser(data.userId, data.request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
      setIsEditDialogOpen(false)
      setSelectedUser(null)
      toast.success("User updated successfully")
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update user")
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
      toast.error(error.response?.data?.detail || "Failed to delete user")
    },
  })

  const handleEdit = (user: UserResponse) => {
    setSelectedUser(user)
    setEditForm({
      is_pro: user.is_pro,
      is_superuser: user.is_superuser,
      daily_ai_usage: user.daily_ai_usage,
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
    updateUserMutation.mutate({
      userId: selectedUser.id,
      request: editForm,
    })
  }

  const handleConfirmDelete = () => {
    if (!selectedUser) return
    deleteUserMutation.mutate(selectedUser.id)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(0)
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
                  placeholder="Search by email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit">Search</Button>
              {searchQuery && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setSearchQuery("")
                    setPage(0)
                  }}
                >
                  Clear
                </Button>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card>
          <CardHeader>
            <CardTitle>All Users</CardTitle>
            <CardDescription>
              {users?.length || 0} user{users?.length !== 1 ? "s" : ""} found
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading users...</div>
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
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.email}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {user.is_superuser && (
                              <Badge variant="destructive" className="gap-1">
                                <ShieldCheck className="h-3 w-3" />
                                Admin
                              </Badge>
                            )}
                            {!user.is_superuser && (
                              <Badge variant="outline" className="gap-1">
                                <UserIcon className="h-3 w-3" />
                                User
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {user.is_pro ? (
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
                            <span>{user.daily_ai_usage}</span>
                            {user.daily_ai_usage > 0 && (
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
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.strategies_count}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.ai_reports_count}
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
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Pagination */}
            {users && users.length >= limit && (
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-muted-foreground">
                  Showing {page * limit + 1}-{Math.min((page + 1) * limit, users.length)} of many
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={users.length < limit}
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
          <DialogContent>
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
                    checked={editForm.is_pro ?? false}
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
                    checked={editForm.is_superuser ?? false}
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
                  {selectedUser.strategies_count} strategies • {selectedUser.ai_reports_count}{" "}
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

