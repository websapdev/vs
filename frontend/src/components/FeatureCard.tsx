'use client'

import { motion } from 'framer-motion'

interface Feature {
  id: number
  title: string
  description: string
  icon: string
}

export default function FeatureCard({ feature }: { feature: Feature }) {
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: 'easeOut' },
    },
  }

  return (
    <motion.div
      variants={itemVariants}
      className="group bg-white border border-gray-200 rounded-xl p-8 hover:shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer"
    >
      <div className="text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">
        {feature.icon}
      </div>
      <h3 className="text-2xl font-bold text-gray-900 mb-3">
        {feature.title}
      </h3>
      <p className="text-gray-600 leading-relaxed">
        {feature.description}
      </p>
      <div className="mt-6 pt-6 border-t border-gray-200">
        <button
          onClick={() => console.log(`Button clicked: Learn More - ${feature.title}`)}
          className="text-blue-600 hover:text-blue-700 font-semibold text-sm group-hover:translate-x-1 transition-transform duration-300"
        >
          Learn More →
        </button>
      </div>
    </motion.div>
  )
}
