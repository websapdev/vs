'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, BarChart3, CheckCircle, LineChart, Target, Zap } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function Home() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()

  const features = [
    {
      icon: <Zap className="w-10 h-10 text-blue-600" />,
      title: 'Instant Audits',
      description: 'Run comprehensive AI visibility audits in seconds. Get detailed insights into your search presence.'
    },
    {
      icon: <Target className="w-10 h-10 text-purple-600" />,
      title: 'Citation Tracking',
      description: 'Monitor your brand mentions across ChatGPT, Claude, and other AI platforms in real-time.'
    },
    {
      icon: <LineChart className="w-10 h-10 text-green-600" />,
      title: 'Answer Graphs',
      description: 'Visualize how your brand appears in AI-generated responses and identify gaps.'
    },
    {
      icon: <Activity className="w-10 h-10 text-orange-600" />,
      title: 'Smart Playbooks',
      description: 'Get AI-generated action plans to improve your visibility and drive growth.'
    },
    {
      icon: <BarChart3 className="w-10 h-10 text-indigo-600" />,
      title: 'Analytics Dashboard',
      description: 'Track your progress with beautiful charts and comprehensive metrics.'
    },
    {
      icon: <CheckCircle className="w-10 h-10 text-teal-600" />,
      title: 'Automated Reports',
      description: 'Export professional reports in DOCX and Markdown formats instantly.'
    },
  ]

  const handleGetStarted = () => {
    if (isAuthenticated) {
      router.push('/dashboard')
    } else {
      router.push('/signup')
    }
  }

  return (
    <main className="min-h-screen bg-white">
      <Navbar />
      
      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-white via-blue-50 to-purple-50">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center space-y-8"
          >
            <div className="space-y-4">
              <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 leading-tight">
                Visibility Intelligence for{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600">
                  AI-Powered Brands
                </span>
              </h1>
              <p className="text-xl sm:text-2xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
                Run instant visibility audits, monitor citations, and convert SEO insights into growth.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <Button size="lg" onClick={handleGetStarted} className="text-lg px-8 py-6">
                {isAuthenticated ? 'Go to Dashboard' : 'Start Free Audit'}
              </Button>
              <Link href="/pricing">
                <Button size="lg" variant="outline" className="text-lg px-8 py-6">
                  View Pricing
                </Button>
              </Link>
            </div>

            <div className="pt-8 flex items-center justify-center space-x-8 text-sm text-gray-600">
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span>Free QuickScan plan</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span>Instant results</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16 space-y-4"
          >
            <h2 className="text-4xl sm:text-5xl font-bold text-gray-900">
              Everything You Need to Win in AI Search
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Comprehensive tools to understand, monitor, and optimize your AI visibility
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Card className="h-full hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
                  <CardHeader>
                    <div className="mb-4">{feature.icon}</div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                    <CardDescription className="text-base">{feature.description}</CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="space-y-4"
          >
            <h2 className="text-4xl sm:text-5xl font-bold text-white">
              Ready to Dominate AI Search?
            </h2>
            <p className="text-xl text-blue-100">
              Join forward-thinking brands using Vysalytica to win in the AI era
            </p>
            <div className="pt-4">
              <Button size="lg" variant="outline" onClick={handleGetStarted} className="bg-white text-blue-600 hover:bg-gray-50 text-lg px-8 py-6 border-0">
                {isAuthenticated ? 'Go to Dashboard' : 'Get Started Free'}
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      <Footer />
    </main>
  )
}
