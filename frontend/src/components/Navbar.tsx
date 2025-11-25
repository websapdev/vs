'use client'

import { useState } from 'react'

export default function Navbar() {
  const handleButtonClick = (buttonName: string) => {
    console.log(`Button clicked: ${buttonName}`)
  }

  return (
    <nav className="fixed top-0 w-full bg-white border-b border-gray-200 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <span className="text-2xl font-bold text-blue-600">Vysalytica</span>
          </div>

          {/* Center Nav Links */}
          <div className="hidden md:flex gap-8">
            <a
              href="#features"
              className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
            >
              Features
            </a>
            <a
              href="#pricing"
              className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
            >
              Pricing
            </a>
            <a
              href="#partners"
              className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
            >
              Partners
            </a>
          </div>

          {/* CTA Button */}
          <button
            onClick={() => handleButtonClick('Get Started')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
          >
            Get Started
          </button>
        </div>
      </div>
    </nav>
  )
}
