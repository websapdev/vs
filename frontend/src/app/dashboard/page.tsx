'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { apiClient } from '@/lib/api'
import Navbar from '@/components/Navbar'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Activity, BarChart3, Eye, FileText, Loader2, TrendingUp, Zap } from 'lucide-react'
import { formatDate, formatScore } from '@/lib/utils'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

export default function DashboardPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  const { data: auditHistory, isLoading } = useQuery({
    queryKey: ['audit-history'],
    queryFn: async () => {
      const response = await apiClient.getAuditHistory(undefined, 10)
      return response.data || []
    },
    enabled: isAuthenticated,
  })

  if (!isAuthenticated) {
    return null
  }

  const totalAudits = auditHistory?.length || 0
  const avgScore = auditHistory && auditHistory.length > 0
    ? Math.round(auditHistory.reduce((sum, audit) => sum + audit.overall_score, 0) / auditHistory.length)
    : 0

  const chartData = auditHistory?.slice(0, 7).reverse().map((audit, index) => ({
    name: `Audit ${index + 1}`,
    score: Math.round(audit.overall_score),
  })) || []

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-24 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header */}
          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-lg text-gray-600">Welcome back, {user?.name || user?.email}</p>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Link href="/audit">
              <Card className="hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-blue-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Run New Audit</CardTitle>
                  <Zap className="w-5 h-5 text-blue-600" />
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-gray-600">Start a visibility audit</p>
                </CardContent>
              </Card>
            </Link>

            <Link href="/citations">
              <Card className="hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-purple-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Track Citations</CardTitle>
                  <Eye className="w-5 h-5 text-purple-600" />
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-gray-600">Monitor brand mentions</p>
                </CardContent>
              </Card>
            </Link>

            <Link href="/pricing">
              <Card className="hover:shadow-lg transition-all cursor-pointer border-2 border-transparent hover:border-green-500">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Upgrade Plan</CardTitle>
                  <TrendingUp className="w-5 h-5 text-green-600" />
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-gray-600">View pricing options</p>
                </CardContent>
              </Card>
            </Link>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Total Audits</CardTitle>
                <FileText className="w-5 h-5 text-gray-400" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-gray-900">{totalAudits}</div>
                <p className="text-xs text-gray-500 mt-1">All time</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Average Score</CardTitle>
                <BarChart3 className="w-5 h-5 text-gray-400" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-gray-900">{avgScore}%</div>
                <p className="text-xs text-gray-500 mt-1">Across all audits</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">Active Brands</CardTitle>
                <Activity className="w-5 h-5 text-gray-400" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-gray-900">{new Set(auditHistory?.map(a => a.domain)).size || 0}</div>
                <p className="text-xs text-gray-500 mt-1">Unique domains</p>
              </CardContent>
            </Card>
          </div>

          {/* Score Trend Chart */}
          {chartData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Score Trend</CardTitle>
                <CardDescription>Your audit scores over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <XAxis dataKey="name" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#ffffff', 
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px'
                      }}
                    />
                    <Line type="monotone" dataKey="score" stroke="#2563eb" strokeWidth={3} dot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Recent Audits */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent Audits</CardTitle>
                  <CardDescription>Your latest visibility audits</CardDescription>
                </div>
                <Link href="/audit">
                  <Button size="sm">Run New Audit</Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                </div>
              ) : auditHistory && auditHistory.length > 0 ? (
                <div className="space-y-4">
                  {auditHistory.map((audit) => (
                    <div
                      key={audit.id}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{audit.domain}</h4>
                        <p className="text-sm text-gray-600">{audit.url}</p>
                        <div className="flex items-center space-x-4 mt-2">
                          <span className="text-xs text-gray-500">
                            {audit.page_count} pages scanned
                          </span>
                          <span className="text-xs text-gray-500">
                            {formatDate(audit.created_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <div className="text-2xl font-bold text-gray-900">
                            {formatScore(audit.overall_score)}%
                          </div>
                          <Badge variant={audit.overall_score >= 80 ? 'success' : audit.overall_score >= 60 ? 'warning' : 'error'}>
                            {audit.overall_score >= 80 ? 'Excellent' : audit.overall_score >= 60 ? 'Good' : 'Needs Work'}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-4">No audits yet</p>
                  <Link href="/audit">
                    <Button>Run Your First Audit</Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
