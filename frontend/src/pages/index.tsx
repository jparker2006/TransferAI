import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { motion, useInView } from 'framer-motion';

// Enhanced Stats Grid Component
const StatsGrid = () => {
  const stats = [
    { 
      value: "86%", 
      label: "Admission Likelihood", 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      )
    },
    { 
      value: "1000+", 
      label: "IGETC Plans Checked", 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    { 
      value: "300+", 
      label: "Successful CCC to UC Transfers", 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
        </svg>
      )
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          className="text-center"
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: i * 0.2 }}
        >
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-2xl flex items-center justify-center">
              {stat.icon}
            </div>
          </div>
          <motion.div
            className="text-4xl font-bold text-white mb-2"
            initial={{ scale: 0.8 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: i * 0.2 + 0.3 }}
          >
            {stat.value}
          </motion.div>
          <div className="text-slate-400 text-sm">{stat.label}</div>
        </motion.div>
      ))}
    </div>
  );
};

// Interactive Transfer Planner Preview
const PlannerPreview = () => {
  const [activeStep, setActiveStep] = useState(0);
  const steps = [
    { 
      id: 'courses', 
      label: 'Your Courses', 
      description: 'Upload your transcripts', 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      )
    },
    { 
      id: 'igetc', 
      label: 'IGETC', 
      description: 'Check general education', 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    { 
      id: 'major', 
      label: 'Major Prep', 
      description: 'Review prerequisites', 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      )
    },
    { 
      id: 'admission', 
      label: 'UC Admission', 
      description: 'Calculate your odds', 
      icon: (
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
        </svg>
      )
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full">
      <div className="bg-gradient-to-r from-slate-900/50 to-slate-800/50 backdrop-blur-xl rounded-3xl border border-slate-700/50 p-8 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-blue-500/5 to-purple-500/5" />
        
        <div className="relative">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-2xl font-semibold text-white">Your Transfer Journey</h3>
            <div className="text-sm text-slate-400">Step {activeStep + 1} of {steps.length}</div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {steps.map((step, i) => (
              <motion.div
                key={step.id}
                className={`relative p-6 rounded-2xl border transition-all duration-500 ${
                  i === activeStep 
                    ? 'bg-gradient-to-r from-emerald-500/20 to-blue-500/20 border-emerald-500/50' 
                    : 'bg-slate-800/30 border-slate-700/30'
                }`}
                animate={{
                  scale: i === activeStep ? 1.05 : 1,
                  opacity: i === activeStep ? 1 : 0.7
                }}
                transition={{ duration: 0.5 }}
              >
                <div className="text-center">
                  <div className="flex items-center justify-center mb-3">
                    <div className="w-12 h-12 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-2xl flex items-center justify-center">
                      {step.icon}
                    </div>
                  </div>
                  <h4 className="text-white font-semibold mb-2">{step.label}</h4>
                  <p className="text-slate-400 text-sm">{step.description}</p>
                </div>
                
                {i < steps.length - 1 && (
                  <div className="absolute -right-3 top-1/2 transform -translate-y-1/2 hidden md:block">
                    <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Live Advisor Chat Preview Component
const LiveAdvisorChat = () => {
  const [demoStep, setDemoStep] = useState<number>(0);
  const [currentThoughtStep, setCurrentThoughtStep] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Demo sequence steps
  const demoSteps = [
    { type: 'user', content: "Do I need a lab for Area 5?", timestamp: "3:42 PM", delay: 1000 },
    { type: 'thinking', content: "", delay: 1500 },
    { type: 'ai', content: "You've already satisfied Area 5B with your Biology course. No additional lab is required for IGETC completion.", timestamp: "3:42 PM", delay: 4000 },
    { type: 'user', content: "What about UC Davis requirements?", timestamp: "3:43 PM", delay: 2000 },
    { type: 'thinking', content: "", delay: 1500 },
    { type: 'ai', content: "For UC Davis, you'll need 2 additional upper-division courses in your major. I recommend CHEM 12A and MATH 2A based on your transcript.", timestamp: "3:43 PM", delay: 4000 },
    { type: 'reset', content: "", delay: 2000 }
  ];

  const thoughtSteps = [
    { text: "Analyzing your transcript...", detail: "Checking completed courses and grades" },
    { text: "Accessing ASSIST database...", detail: "Connecting to UC articulation system" },
    { text: "Cross-referencing IGETC requirements...", detail: "Validating Area 5 science requirements" },
    { text: "Verifying course equivalencies...", detail: "Biology 3 → Physical Science + Lab credit" }
  ];

  const runNextStep = () => {
    if (demoStep >= demoSteps.length) {
      // Reset demo
      setDemoStep(0);
      setCurrentThoughtStep(0);
      setIsComplete(false);
      timeoutRef.current = setTimeout(() => runNextStep(), 1000);
      return;
    }

    const step = demoSteps[demoStep];
    
    if (step.type === 'reset') {
      setDemoStep(0);
      setCurrentThoughtStep(0);
      setIsComplete(false);
      timeoutRef.current = setTimeout(() => runNextStep(), step.delay);
      return;
    }

    setDemoStep(prev => prev + 1);
    
    if (step.type === 'thinking') {
      // Start thought progression
      setCurrentThoughtStep(0);
      setIsComplete(false);
      
      // Progress through thought steps
      const progressThoughts = (stepIndex: number) => {
        if (stepIndex < thoughtSteps.length) {
          setCurrentThoughtStep(stepIndex);
          setTimeout(() => progressThoughts(stepIndex + 1), 800);
        } else {
          setIsComplete(true);
        }
      };
      
      setTimeout(() => progressThoughts(0), 300);
    }
    
    timeoutRef.current = setTimeout(() => runNextStep(), step.delay);
  };

  // Get current messages to display
  const getCurrentMessages = () => {
    const messages = [];
    
    for (let i = 0; i < demoStep; i++) {
      const step = demoSteps[i];
      if (step.type !== 'reset' && step.type !== 'thinking') {
        messages.push(step);
      }
    }
    
    // Add thinking message if currently thinking
    if (demoStep > 0 && demoSteps[demoStep - 1]?.type === 'thinking') {
      messages.push({ type: 'thinking', content: "", timestamp: "" });
    }
    
    return messages;
  };

  useEffect(() => {
    if (!inView) return;

    // Start demo after component is in view
    timeoutRef.current = setTimeout(() => {
      runNextStep();
    }, 1000);
    
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [inView, runNextStep]);

  return (
    <div ref={ref} className="relative">
      <motion.div
        className="bg-slate-900/50 backdrop-blur-xl rounded-3xl border border-slate-700/50 shadow-2xl overflow-hidden"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        whileInView={{ opacity: 1, scale: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
      >
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-slate-800/50 to-slate-700/50 p-4 border-b border-slate-700/50">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full flex items-center justify-center mr-3">
              <span className="text-white font-bold text-lg">A</span>
            </div>
            <div className="flex-1">
              <h3 className="text-white font-semibold">Advisity Assistant</h3>
              <div className="flex items-center text-emerald-400 text-sm">
                <div className="w-2 h-2 bg-emerald-400 rounded-full mr-2 animate-pulse"></div>
                <span>Online</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="p-6 space-y-4 min-h-[400px] max-h-[400px] overflow-hidden">
          {getCurrentMessages().map((message: any, index: number) => (
            <motion.div
              key={`${index}-${message.type}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} items-end space-x-2`}
            >
              {message.type !== 'user' && (
                <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold text-sm">A</span>
                </div>
              )}

              <div className={`flex flex-col ${message.type === 'user' ? 'items-end' : 'items-start'}`}>
                {message.type === 'thinking' ? (
                  <div className="bg-slate-800/50 px-4 py-3 rounded-2xl rounded-bl-md border border-slate-700/50">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2 mb-3">
                    <div className="flex space-x-1">
                      {[0, 1, 2].map((i) => (
                        <motion.div
                          key={i}
                          className="w-2 h-2 bg-emerald-400 rounded-full"
                          animate={{ 
                                scale: [1, 1.3, 1],
                            opacity: [0.5, 1, 0.5]
                          }}
                          transition={{
                                duration: 1.2,
                            repeat: Infinity,
                                delay: i * 0.3
                          }}
                        />
                      ))}
                    </div>
                        <span className="text-emerald-400 text-sm font-medium">Chain of Thought</span>
                      </div>
                      
                      {/* Thought steps */}
                      <div className="space-y-1">
                        {thoughtSteps.slice(0, Math.max(1, currentThoughtStep + 1)).map((step, i) => (
                          <motion.div
                            key={i}
                            className={`flex items-center space-x-2 text-xs ${
                              i <= currentThoughtStep ? 'text-emerald-400' : 'text-slate-500'
                            }`}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className={`w-1.5 h-1.5 rounded-full ${
                              i < currentThoughtStep || isComplete ? 'bg-emerald-400' : 
                              i === currentThoughtStep ? 'bg-emerald-400' : 'bg-slate-600'
                            }`}>
                              {(i < currentThoughtStep || isComplete) && (
                                <svg className="w-1.5 h-1.5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                                </svg>
                              )}
                            </div>
                            <div className="flex-1">
                              <div className="font-medium">{step.text}</div>
                              <div className="text-slate-600 text-xs">{step.detail}</div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col space-y-1">
                    <div className={`px-4 py-3 rounded-2xl max-w-sm ${
                      message.type === 'user'
                        ? 'bg-gradient-to-r from-emerald-600 to-blue-600 text-white rounded-br-md'
                        : 'bg-slate-800/50 text-white border border-slate-700/50 rounded-bl-md'
                    }`}>
                      {message.content}
                    </div>
                    {message.timestamp && (
                      <span className={`text-xs text-slate-500 ${message.type === 'user' ? 'text-right' : 'text-left'}`}>
                        {message.timestamp}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {message.type === 'user' && (
                <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                  </svg>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-slate-700/50 bg-slate-900/20">
          <div className="flex items-center space-x-3">
            <div className="flex-1 bg-slate-800/50 rounded-full px-4 py-3 border border-slate-700/50">
              <input 
                type="text" 
                placeholder="Ask anything about transferring..."
                className="w-full bg-transparent text-white placeholder-slate-400 text-sm focus:outline-none"
                disabled
              />
            </div>
            <motion.button 
              className="w-10 h-10 bg-gradient-to-r from-emerald-600 to-blue-600 rounded-full flex items-center justify-center"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
              </svg>
            </motion.button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// Animated Showcase Component
const AnimatedShowcase = () => {
  const [currentState, setCurrentState] = useState(0);
  const states = ['odds', 'schedule', 'chat', 'gpa', 'deadlines'];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentState((prev) => (prev + 1) % 5);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full h-[500px] bg-gradient-to-tr from-[#0F172A] to-[#101F33] rounded-3xl backdrop-blur-xl shadow-2xl border border-slate-700/50 overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 via-blue-500/5 to-purple-500/5" />
      
      {/* State 1: Admission Chances Calculator */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center p-6"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ 
          opacity: currentState === 0 ? 1 : 0,
          scale: currentState === 0 ? 1 : 0.8
        }}
        transition={{ duration: 1, ease: "easeInOut" }}
      >
        <div className="w-full max-w-sm space-y-4">
          {/* Header */}
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ 
              opacity: currentState === 0 ? 1 : 0,
              y: currentState === 0 ? 0 : 20
            }}
            transition={{ delay: 0.5 }}
          >
            <div className="text-slate-400 text-sm mb-1">Your Admission Chances</div>
            <div className="text-emerald-400 text-lg font-bold">After Completing Plan</div>
          </motion.div>

          {/* University Cards */}
          <motion.div
            className="space-y-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ 
              opacity: currentState === 0 ? 1 : 0,
              y: currentState === 0 ? 0 : 20
            }}
            transition={{ delay: 0.8 }}
          >
            {[
              { name: 'UCLA', chance: 89, color: 'from-blue-500 to-blue-600', increase: '+37%' },
              { name: 'UCSD', chance: 92, color: 'from-emerald-500 to-emerald-600', increase: '+40%' },
              { name: 'UCI', chance: 95, color: 'from-purple-500 to-purple-600', increase: '+43%' }
            ].map((school, i) => (
              <motion.div
                key={school.name}
                className="flex items-center justify-between p-3 bg-slate-800/40 rounded-xl border border-slate-700/50 backdrop-blur-sm"
                initial={{ opacity: 0, x: -20, scale: 0.9 }}
                animate={{ 
                  opacity: currentState === 0 ? 1 : 0,
                  x: currentState === 0 ? 0 : -20,
                  scale: currentState === 0 ? 1 : 0.9
                }}
                transition={{ delay: 1 + i * 0.1 }}
              >
                <div className="flex items-center space-x-3">
                  <div className={`w-8 h-8 bg-gradient-to-r ${school.color} rounded-lg flex items-center justify-center`}>
                    <span className="text-white text-xs font-bold">{school.name.slice(0, 2)}</span>
                  </div>
                  <div>
                    <div className="text-white font-medium text-sm">{school.name}</div>
                    <div className="text-emerald-400 text-xs font-medium">{school.increase}</div>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div className="flex items-center space-x-3">
                  <div className="w-16 bg-slate-700 rounded-full h-2 overflow-hidden">
                    <motion.div
                      className={`h-full bg-gradient-to-r ${school.color}`}
                      initial={{ width: '0%' }}
                      animate={{ width: currentState === 0 ? `${school.chance}%` : '0%' }}
                      transition={{ delay: 1.2 + i * 0.1, duration: 1 }}
                    />
                  </div>
                  <div className="text-white font-bold text-sm w-8">{school.chance}%</div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Summary */}
          <motion.div
            className="text-center bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-xl p-3 border border-emerald-500/30"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ 
              opacity: currentState === 0 ? 1 : 0,
              scale: currentState === 0 ? 1 : 0.9
            }}
            transition={{ delay: 1.8 }}
          >
            <div className="flex items-center justify-center space-x-2">
              <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
              </svg>
              <span className="text-emerald-400 text-sm font-medium">Strong UC Prospects</span>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* State 2: Schedule Builder */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center p-6"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ 
          opacity: currentState === 1 ? 1 : 0,
          scale: currentState === 1 ? 1 : 0.8
        }}
        transition={{ duration: 1, ease: "easeInOut" }}
      >
        <div className="w-full max-w-sm">
          {/* Calendar grid */}
          <div className="space-y-4">
            <div className="text-center text-slate-400 text-sm mb-4">Fall 2025</div>
            
            {/* Course blocks */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { code: 'CIS 36A', name: 'Java Programming', color: 'from-blue-500 to-blue-600' },
                { code: 'MATH 1C', name: 'Calculus III', color: 'from-emerald-500 to-emerald-600' },
                { code: 'PHYS 4A', name: 'Physics', color: 'from-purple-500 to-purple-600' },
                { code: 'ENGL 1A', name: 'Composition', color: 'from-orange-500 to-orange-600' }
              ].map((course, i) => (
                <motion.div
                  key={course.code}
                  className={`p-3 rounded-xl bg-gradient-to-r ${course.color} text-white shadow-lg`}
                  initial={{ opacity: 0, y: 20, scale: 0.9 }}
                  animate={{ 
                    opacity: currentState === 1 ? 1 : 0,
                    y: currentState === 1 ? 0 : 20,
                    scale: currentState === 1 ? 1 : 0.9
                  }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                >
                  <div className="font-semibold text-sm">{course.code}</div>
                  <div className="text-xs opacity-90 leading-tight">{course.name}</div>
                </motion.div>
              ))}
            </div>
            
            {/* IGETC completion badge */}
            <motion.div
              className="flex items-center justify-center mt-4"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ 
                opacity: currentState === 1 ? 1 : 0,
                scale: currentState === 1 ? 1 : 0.8
              }}
              transition={{ delay: 1.5 }}
            >
              <div className="bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-full text-sm font-medium border border-emerald-500/30">
                <svg className="w-4 h-4 mr-2 inline" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                </svg>
                IGETC Area 5
              </div>
            </motion.div>
          </div>
        </div>
      </motion.div>

      {/* State 3: AI Chat Interface */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center p-6"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ 
          opacity: currentState === 2 ? 1 : 0,
          scale: currentState === 2 ? 1 : 0.8
        }}
        transition={{ duration: 1, ease: "easeInOut" }}
      >
        <div className="w-full max-w-xs space-y-3">
          {/* User message */}
          <motion.div
            className="flex justify-end"
            initial={{ opacity: 0, x: 20 }}
            animate={{ 
              opacity: currentState === 2 ? 1 : 0,
              x: currentState === 2 ? 0 : 20
            }}
            transition={{ delay: 0.5 }}
          >
            <div className="bg-emerald-600 text-white px-3 py-2 rounded-2xl rounded-br-md max-w-[200px]">
              <div className="text-sm">Do I need a lab for Area 5?</div>
            </div>
          </motion.div>
          
          {/* Thinking indicator */}
          <motion.div
            className="flex justify-start"
            initial={{ opacity: 0 }}
            animate={{ 
              opacity: currentState === 2 ? [0, 1, 1, 0] : 0
            }}
            transition={{ 
              delay: 1,
              times: [0, 0.2, 0.8, 1],
              duration: 1.5
            }}
          >
            <div className="bg-slate-700/80 px-3 py-2 rounded-2xl rounded-bl-md border border-slate-600/50">
              <div className="flex items-center space-x-2">
                <motion.div
                  className="w-3 h-3 bg-blue-400 rounded-full"
                  animate={currentState === 2 ? {
                    scale: [1, 1.2, 1],
                    opacity: [0.6, 1, 0.6]
                  } : {
                    scale: 1,
                    opacity: 0.6
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: currentState === 2 ? Infinity : 0,
                    ease: "easeInOut"
                  }}
                />
                <span className="text-blue-400 text-xs font-medium">Checking transcript...</span>
              </div>
            </div>
          </motion.div>
          
          {/* AI response */}
          <motion.div
            className="flex justify-start"
            initial={{ opacity: 0, x: -20 }}
            animate={{ 
              opacity: currentState === 2 ? 1 : 0,
              x: currentState === 2 ? 0 : -20
            }}
            transition={{ delay: 2.5 }}
          >
            <div className="bg-slate-700 text-white px-3 py-2 rounded-2xl rounded-bl-md max-w-[240px]">
              <div className="text-sm leading-tight">You've already satisfied Area 5B with Biology 3. No additional lab required.</div>
            </div>
          </motion.div>
          
          {/* Chain of thought */}
          <motion.div
            className="flex justify-start"
            initial={{ opacity: 0, x: -20 }}
            animate={{ 
              opacity: currentState === 2 ? 1 : 0,
              x: currentState === 2 ? 0 : -20
            }}
            transition={{ delay: 3.2 }}
          >
            <div className="bg-slate-800/60 text-slate-300 px-3 py-2 rounded-2xl rounded-bl-md max-w-[240px] border border-slate-600/30">
              <div className="text-xs leading-tight">
                <div className="flex items-center space-x-1 mb-1">
                  <svg className="w-3 h-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  <span className="font-medium text-emerald-400">Verified with ASSIST</span>
                </div>
                <div>Bio 3 = Physical Science + Lab requirement</div>
              </div>
            </div>
          </motion.div>
          
          {/* Advisity AI badge */}
          <motion.div
            className="flex justify-center mt-2"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ 
              opacity: currentState === 2 ? 1 : 0,
              scale: currentState === 2 ? 1 : 0.8
            }}
            transition={{ delay: 3.8 }}
          >
            <div className="flex items-center space-x-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-600">
              <motion.div
                className="w-5 h-5 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full flex items-center justify-center"
                animate={{ 
                  scale: currentState === 2 ? [1, 1.1, 1] : 1
                }}
                transition={{ delay: 4, duration: 0.5 }}
              >
                <span className="text-white text-xs font-bold">A</span>
              </motion.div>
              <span className="text-slate-300 text-xs">Advisity AI</span>
            </div>
          </motion.div>
        </div>
      </motion.div>
      
      {/* State 4: GPA Calculator */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center p-6"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ 
          opacity: currentState === 3 ? 1 : 0,
          scale: currentState === 3 ? 1 : 0.8
        }}
        transition={{ duration: 1, ease: "easeInOut" }}
      >
        <div className="w-full max-w-xs space-y-4">
          {/* GPA Display */}
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ 
              opacity: currentState === 3 ? 1 : 0,
              y: currentState === 3 ? 0 : 20
            }}
            transition={{ delay: 0.5 }}
          >
            <div className="text-slate-400 text-sm mb-1">Current GPA</div>
            <div className="text-4xl font-bold text-white mb-1">3.7</div>
            <div className="text-emerald-400 text-sm font-medium">Target: 3.8+</div>
          </motion.div>
          
          {/* Grade breakdown */}
          <motion.div
            className="space-y-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ 
              opacity: currentState === 3 ? 1 : 0,
              y: currentState === 3 ? 0 : 20
            }}
            transition={{ delay: 0.8 }}
          >
            {[
              { grade: 'A', count: 8, width: '60%', color: 'bg-emerald-500' },
              { grade: 'B', count: 4, width: '30%', color: 'bg-blue-500' },
              { grade: 'C', count: 1, width: '10%', color: 'bg-yellow-500' }
            ].map((item, i) => (
              <div key={item.grade} className="flex items-center space-x-2">
                <div className="w-6 text-slate-400 text-sm">{item.grade}:</div>
                <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
                  <motion.div
                    className={`h-full ${item.color}`}
                    initial={{ width: 0 }}
                    animate={{ width: currentState === 3 ? item.width : 0 }}
                    transition={{ delay: 1 + i * 0.2, duration: 0.8 }}
                  />
                </div>
                <div className="text-slate-400 text-sm w-5">{item.count}</div>
              </div>
            ))}
          </motion.div>
          
          {/* Prediction */}
          <motion.div
            className="text-center bg-slate-800/50 rounded-2xl p-3"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ 
              opacity: currentState === 3 ? 1 : 0,
              scale: currentState === 3 ? 1 : 0.9
            }}
            transition={{ delay: 1.5 }}
          >
            <div className="text-emerald-400 text-sm font-medium mb-1">Prediction</div>
            <div className="text-white text-xs">Need 2 more A's to reach 3.8 GPA</div>
          </motion.div>
        </div>
      </motion.div>

      {/* State 5: Deadlines */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center p-6"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ 
          opacity: currentState === 4 ? 1 : 0,
          scale: currentState === 4 ? 1 : 0.8
        }}
        transition={{ duration: 1, ease: "easeInOut" }}
      >
        <div className="w-full max-w-sm space-y-4">
          {/* Header */}
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ 
              opacity: currentState === 4 ? 1 : 0,
              y: currentState === 4 ? 0 : 20
            }}
            transition={{ delay: 0.5 }}
          >
            <div className="text-slate-400 text-sm mb-1">Upcoming Deadlines</div>
            <div className="text-xl font-bold text-white">Fall 2025 Transfer</div>
          </motion.div>
          
          {/* Timeline */}
          <motion.div
            className="space-y-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ 
              opacity: currentState === 4 ? 1 : 0,
              y: currentState === 4 ? 0 : 20
            }}
            transition={{ delay: 0.8 }}
          >
            {[
              { date: 'Oct 1', task: 'UC App Opens', status: 'active', color: 'border-emerald-500' },
              { date: 'Nov 30', task: 'UC App Due', status: 'upcoming', color: 'border-blue-500' },
              { date: 'Jan 31', task: 'FAFSA Due', status: 'upcoming', color: 'border-yellow-500' }
            ].map((item, i) => (
              <motion.div
                key={item.date}
                className={`flex items-center space-x-3 p-2 rounded-lg border ${item.color} bg-slate-800/30`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ 
                  opacity: currentState === 4 ? 1 : 0,
                  x: currentState === 4 ? 0 : -20
                }}
                transition={{ delay: 1 + i * 0.1 }}
              >
                <div className="w-10 text-center">
                  <div className="text-white text-xs font-medium">{item.date}</div>
                </div>
                <div className="flex-1">
                  <div className="text-white text-sm">{item.task}</div>
                </div>
                <div className={`w-2 h-2 rounded-full ${
                  item.status === 'active' ? 'bg-emerald-500' : 
                  item.status === 'upcoming' ? 'bg-blue-500' : 'bg-slate-600'
                }`} />
              </motion.div>
            ))}
          </motion.div>
          
          {/* Days remaining */}
          <motion.div
            className="text-center bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-2xl p-3 border border-emerald-500/30"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ 
              opacity: currentState === 4 ? 1 : 0,
              scale: currentState === 4 ? 1 : 0.9
            }}
            transition={{ delay: 1.5 }}
          >
            <div className="text-emerald-400 text-sm font-medium mb-1">Next Deadline</div>
            <div className="text-white text-lg font-semibold">38 days remaining</div>
          </motion.div>
        </div>
      </motion.div>
      
      {/* State indicators */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2">
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-slate-600"
            animate={{
              backgroundColor: currentState === i ? '#10b981' : '#475569'
            }}
            transition={{ duration: 0.3 }}
          />
        ))}
      </div>
    </div>
  );
};

// Hero Backdrop Component
const HeroBackdrop = () => {
  return (
    <div className="absolute inset-0 z-[-1] overflow-hidden">
      {/* Primary flowing stripe */}
      <motion.div
        className="absolute inset-0 opacity-[0.08]"
        style={{
          background: 'linear-gradient(135deg, transparent 0%, rgba(16, 185, 129, 0.4) 25%, rgba(6, 182, 212, 0.4) 50%, rgba(59, 130, 246, 0.4) 75%, transparent 100%)',
          transform: 'translateX(-50%) translateY(-50%) rotate(-15deg) scale(1.5)',
        }}
        animate={{
          translateX: ['-60%', '-40%', '-60%'],
          translateY: ['-60%', '-40%', '-60%'],
          rotate: [-15, -10, -15],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Ambient glow */}
      <motion.div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, rgba(16, 185, 129, 0.3) 0%, transparent 70%)',
          filter: 'blur(150px)',
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.04, 0.08, 0.04],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
    </div>
  );
};

// Main Landing Page Component
const LandingPage: React.FC = () => {

  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-x-hidden relative">
      {/* Sophisticated Background */}
      <div className="fixed inset-0 -z-20">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_var(--tw-gradient-stops))] from-emerald-900/20 via-transparent to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent" />
        
        {/* Subtle floating elements */}
        {[...Array(3)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-64 h-64 rounded-full opacity-5 blur-3xl"
            style={{
              left: `${20 + i * 30}%`,
              top: `${20 + i * 20}%`,
              background: i % 2 === 0 ? '#10b981' : '#3b82f6'
            }}
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.05, 0.1, 0.05]
            }}
            transition={{
              duration: 8 + i * 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        ))}
      </div>

      {/* Header */}
      <motion.header 
        className="fixed top-0 w-full z-50 backdrop-blur-xl bg-slate-950/80 border-b border-slate-800"
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <div className="px-8 py-4 flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-blue-500 rounded-xl mr-3 flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-lg">A</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Advisity</h1>
          </div>
          
          <nav className="hidden md:flex items-center space-x-8">
            {['Features', 'How it Works', 'Pricing'].map((item, i) => (
              <motion.a
                key={item}
                href={`#${item.toLowerCase().replace(' ', '-')}`}
                className="relative text-slate-400 hover:text-white transition-colors font-medium"
                whileHover={{ scale: 1.05 }}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 + 0.5 }}
                aria-label={`Navigate to ${item} section`}
              >
                {item}
                <motion.div
                  className="absolute -bottom-1 left-0 h-0.5 bg-gradient-to-r from-emerald-500 to-blue-500"
                  initial={{ width: 0 }}
                  whileHover={{ width: '100%' }}
                  transition={{ duration: 0.3 }}
                />
              </motion.a>
            ))}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.8 }}
            >
              <Link
                href="/chat"
                className="px-6 py-3 bg-gradient-to-r from-emerald-600 to-blue-600 rounded-full font-semibold hover:shadow-lg hover:shadow-emerald-500/25 transition-all hover:scale-105"
                aria-label="Start using Advisity now"
              >
                Get Started
              </Link>
            </motion.div>
          </nav>
        </div>
      </motion.header>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center overflow-hidden" aria-label="Hero section with main product introduction">
        <HeroBackdrop />
        <div className="grid grid-cols-1 md:grid-cols-2 items-center gap-12 px-8 py-24 md:py-32 max-w-7xl mx-auto relative z-10">
          
          {/* Left Side - Content */}
          <motion.div 
            className="space-y-6"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, ease: "easeOut" }}
          >
            <motion.h1 
              className="text-5xl md:text-6xl font-bold text-white leading-tight tracking-tight"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              Your UC Transfer Advisor,<br className="hidden md:block" /> 
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
                Powered by AI
              </span>
            </motion.h1>
            
            <motion.p 
              className="text-slate-400 text-lg max-w-md leading-relaxed"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              Advisity shows you what transfers, what's missing, and how to graduate — instantly and accurately.
            </motion.p>
            
            <motion.div 
              className="flex flex-col sm:flex-row gap-4 pt-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
            >
              <Link 
                href="/chat"
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-8 py-4 rounded-full shadow-lg hover:shadow-emerald-500/25 transition-all hover:scale-105 text-center"
                aria-label="Get started with Advisity transfer planning"
              >
                Get Started
              </Link>
              <button 
                className="bg-slate-800 hover:bg-slate-700 text-slate-100 font-medium px-8 py-4 rounded-full border border-slate-600 transition-all hover:scale-105"
                aria-label="Watch product demonstration video"
              >
                Watch Demo
              </button>
            </motion.div>
          </motion.div>

          {/* Right Side - Animated Showcase */}
          <motion.div
            className="relative"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, ease: "easeOut", delay: 0.3 }}
          >
            <AnimatedShowcase />
          </motion.div>
        </div>
        
        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex flex-col items-center space-y-2 z-20"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 2 }}
        >
          <div className="text-slate-400 text-sm font-medium">See more below</div>
          <motion.div
            className="w-6 h-6 border-2 border-slate-400 rounded-full flex items-center justify-center"
            animate={{ 
              y: [0, 8, 0],
              opacity: [0.5, 1, 0.5]
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          >
            <svg 
              className="w-3 h-3 text-slate-400" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M19 14l-7 7m0 0l-7-7m7 7V3" 
              />
            </svg>
          </motion.div>
        </motion.div>
      </section>

      {/* Transfer Outcomes Section */}
      <section className="py-24 px-8 relative overflow-hidden" aria-label="Student success statistics and outcomes">
        {/* Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-900/10 via-transparent to-blue-900/10" />
        <div className="absolute inset-0 bg-gradient-to-t from-transparent via-emerald-950/5 to-transparent" />
        
        {/* Floating background elements */}
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-gradient-to-br from-emerald-500/5 to-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-48 h-48 bg-gradient-to-br from-blue-500/5 to-emerald-500/5 rounded-full blur-3xl" />
        
        <div className="max-w-7xl mx-auto relative">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl md:text-6xl font-semibold text-white leading-tight mb-6">
              Built to Get You{' '}
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
                Admitted
              </span>
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              Join hundreds of CCC students who've successfully transferred to their dream UC schools with Advisity's guidance
            </p>
          </motion.div>
          
          <StatsGrid />
        </div>
      </section>

      {/* Live Advisor Chat Preview Section */}
      <section className="py-24 px-8 max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            className="space-y-6"
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1 }}
          >
            <div className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-full border border-emerald-500/30">
              <span className="text-emerald-400 text-sm font-medium">Real Student Questions</span>
            </div>
            <h2 className="text-4xl font-semibold text-white leading-tight">
              Ask Anything About{' '}
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
                Transferring
              </span>
            </h2>
            <p className="text-slate-400 text-lg leading-relaxed">
              Get instant, accurate answers to your transfer questions. Always up-to-date with official requirements.
            </p>
            
            <div className="space-y-4">
              <div className="flex items-center space-x-3 text-white/80">
                <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                </svg>
                <span>ASSIST data-backed answers</span>
              </div>
              <div className="flex items-center space-x-3 text-white/80">
                <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                </svg>
                <span>Personalized to your courses</span>
              </div>
              <div className="flex items-center space-x-3 text-white/80">
                <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                </svg>
                <span>Available 24/7</span>
              </div>
            </div>

            <motion.div whileHover={{ scale: 1.02 }} className="pt-4">
              <Link
                href="/chat"
                className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-emerald-600 to-blue-600 rounded-full font-semibold text-white shadow-lg hover:shadow-emerald-500/25 transition-all hover:scale-105 group"
              >
                Start Asking Questions
                <svg className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </Link>
            </motion.div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: 0.3 }}
          >
            <LiveAdvisorChat />
          </motion.div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-24 px-8 relative">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            className="text-center mb-20"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-full border border-emerald-500/30 mb-6">
              <span className="text-emerald-400 text-sm font-medium">Trusted by CCC Students</span>
            </div>
            <h2 className="text-4xl md:text-6xl font-semibold text-white leading-tight mb-6">
              Finally, Transfer Planning{' '}
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
                That Makes Sense
              </span>
            </h2>
            <p className="text-lg text-slate-400 max-w-3xl mx-auto">
              No more confusion, no more stress. Just a clear path to your dream UC school.
            </p>
          </motion.div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
            {[
              {
                title: 'Complete Course Mapping',
                desc: 'See exactly how your CCC courses satisfy UC requirements, organized by priority',
                icon: 'checklist',
                stat: '99%',
                statLabel: 'Accurate mappings'
              },
              {
                title: 'Real-Time ASSIST Data',
                desc: 'Always current with the latest articulation agreements - no outdated information',
                icon: 'refresh',
                stat: 'Live',
                statLabel: 'ASSIST sync'
              },
              {
                title: 'Track Your Progress',
                desc: 'Know exactly where you stand and what courses to prioritize next semester',
                icon: 'progress',
                stat: '86%',
                statLabel: 'Admission odds'
              },
              {
                title: 'Multi-Campus Planning',
                desc: 'Compare requirements across all UC campuses to maximize your options',
                icon: 'compare',
                stat: '9',
                statLabel: 'UC campuses'
              },
              {
                title: 'Alternative Pathways',
                desc: 'Get backup course options when your first choice classes are full',
                icon: 'backup',
                stat: '3+',
                statLabel: 'Course alternatives'
              },
              {
                title: 'Optimize Your Time',
                desc: 'Graduate on schedule and avoid unnecessary courses with smart planning',
                icon: 'savings',
                stat: '2 years',
                statLabel: 'Transfer timeline'
              }
            ].map((feature, i) => (
              <motion.div
                key={feature.title}
                className="relative p-6 lg:p-8 rounded-3xl bg-gradient-to-br from-white/5 to-white/10 border border-white/20 hover:border-white/30 transition-all group"
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: i * 0.1 }}
                whileHover={{ scale: 1.02, y: -2 }}
              >
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-blue-500/5 via-emerald-500/5 to-purple-500/5 rounded-3xl"
                  initial={{ opacity: 0 }}
                  whileHover={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                />
                
                <div className="relative">
                  {/* Stat badge */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-12 h-12 bg-gradient-to-r from-blue-500/20 to-emerald-500/20 rounded-2xl flex items-center justify-center">
                      {feature.icon === 'checklist' && (
                        <svg className="w-6 h-6 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                        </svg>
                      )}
                      {feature.icon === 'refresh' && (
                        <svg className="w-6 h-6 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd"/>
                        </svg>
                      )}
                      {feature.icon === 'progress' && (
                        <svg className="w-6 h-6 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                        </svg>
                      )}
                      {feature.icon === 'compare' && (
                        <svg className="w-6 h-6 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M5 12a1 1 0 102 0V6.414l1.293 1.293a1 1 0 001.414-1.414l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L5 6.414V12zM15 8a1 1 0 10-2 0v5.586l-1.293-1.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L15 13.586V8z"/>
                        </svg>
                      )}
                      {feature.icon === 'backup' && (
                        <svg className="w-6 h-6 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd"/>
                        </svg>
                      )}
                      {feature.icon === 'savings' && (
                        <svg className="w-6 h-6 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"/>
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd"/>
                        </svg>
                      )}
                </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white">{feature.stat}</div>
                      <div className="text-xs text-white/60">{feature.statLabel}</div>
                    </div>
                  </div>
                  
                  <h3 className="text-xl font-bold mb-3 text-white group-hover:text-green-400 transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-white/70 leading-relaxed text-sm lg:text-base">{feature.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>


        </div>
      </section>

      {/* Transfer Pathway Visualization Section */}
      <section className="py-32 px-6 bg-gradient-to-b from-transparent to-blue-950/20">
        <div className="max-w-6xl mx-auto">
          <motion.div 
            className="text-center mb-20"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-5xl md:text-7xl font-bold mb-6">
              Your Transfer{' '}
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
                Pathway
            </span>
            </h2>
            <p className="text-xl text-white/70 max-w-3xl mx-auto">
              See how your SMC courses connect to UC and CSU requirements
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1 }}
      >
            <PlannerPreview />
          </motion.div>
        </div>
      </section>

      {/* Data Accuracy Section */}
      <section className="py-24 px-8 relative overflow-hidden">
        {/* Abstract Background Animations */}
        <div className="absolute inset-0 -z-10">
          {/* Floating geometric shapes */}
          {[...Array(6)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-16 h-16 border border-emerald-500/10 rounded-full"
              style={{
                left: `${15 + i * 15}%`,
                top: `${20 + (i % 3) * 25}%`,
              }}
              animate={{
                y: [0, -20, 0],
                opacity: [0.3, 0.7, 0.3],
                scale: [1, 1.1, 1]
              }}
              transition={{
                duration: 4 + i * 0.5,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 0.8
              }}
            />
          ))}
          
          {/* Data flow lines */}
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: 0.5 }}
          >
            <div className="relative w-full max-w-3xl h-1">
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-emerald-500/20 via-blue-500/20 to-emerald-500/20 h-0.5"
                animate={{
                  background: [
                    "linear-gradient(90deg, rgba(16, 185, 129, 0.2) 0%, rgba(59, 130, 246, 0.2) 50%, rgba(16, 185, 129, 0.2) 100%)",
                    "linear-gradient(90deg, rgba(59, 130, 246, 0.2) 0%, rgba(16, 185, 129, 0.2) 50%, rgba(59, 130, 246, 0.2) 100%)",
                    "linear-gradient(90deg, rgba(16, 185, 129, 0.2) 0%, rgba(59, 130, 246, 0.2) 50%, rgba(16, 185, 129, 0.2) 100%)"
                  ]
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
              
              {/* Data packets */}
              {[...Array(3)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-2 h-2 bg-emerald-400 rounded-full -top-0.5"
                  animate={{
                    x: [0, 600, 0],
                    opacity: [0, 1, 0.7, 1, 0]
                  }}
                  transition={{
                    duration: 4,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 1.3
                  }}
                />
              ))}
            </div>
          </motion.div>
          
          {/* Abstract gradient shapes */}
          <motion.div
            className="absolute top-1/4 left-1/4 w-32 h-32 bg-gradient-to-br from-emerald-500/10 to-blue-500/10 rounded-full blur-3xl"
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.5, 0.8, 0.5]
            }}
            transition={{
              duration: 6,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
          
          <motion.div
            className="absolute bottom-1/4 right-1/4 w-40 h-40 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl"
            animate={{
              scale: [1.2, 1, 1.2],
              opacity: [0.3, 0.6, 0.3]
            }}
            transition={{
              duration: 8,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 2
            }}
          />
        </div>
        
        <div className="max-w-5xl mx-auto relative">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-full border border-emerald-500/30 mb-6">
              <span className="text-emerald-400 text-sm font-medium">Powered by Real Data</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-white">
              Always Accurate,{' '}
              <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
                Always Current
              </span>
            </h2>
            <p className="text-lg text-white/70 max-w-2xl mx-auto">
              Synced directly with official sources, updated daily.
            </p>
          </motion.div>

          {/* Simplified Data Sources */}
          <div className="grid md:grid-cols-2 gap-8 mb-16 relative">

              <motion.div
              className="relative p-8 rounded-3xl bg-gradient-to-br from-white/5 to-white/10 border border-white/20 text-center group"
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              whileHover={{ scale: 1.02, borderColor: "rgba(16, 185, 129, 0.3)" }}
              >
              {/* Animated border glow */}
                    <motion.div
                className="absolute inset-0 rounded-3xl bg-gradient-to-r from-emerald-500/20 via-transparent to-emerald-500/20"
                      animate={{ 
                  opacity: [0, 0.5, 0]
                      }}
                      transition={{
                  duration: 3,
                        repeat: Infinity,
                        ease: "easeInOut"
                      }}
                    />
              
              {/* Data particles */}
              {[...Array(4)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 bg-emerald-400/60 rounded-full"
                  style={{
                    left: `${20 + i * 20}%`,
                    top: `${30 + (i % 2) * 40}%`
                  }}
                  animate={{
                    y: [0, -10, 0],
                    opacity: [0.4, 1, 0.4]
                  }}
                  transition={{
                    duration: 2 + i * 0.3,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 0.5
                  }}
                />
              ))}
              
              <motion.div 
                className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4 relative"
                whileHover={{ rotate: 360 }}
                transition={{ duration: 0.8 }}
              >
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                      </svg>
              </motion.div>
              <h3 className="text-xl font-semibold text-white mb-2">ASSIST Database</h3>
              <p className="text-white/60 text-sm mb-4">Official UC articulation agreements</p>
                <motion.div
                className="text-3xl font-bold text-emerald-400 mb-1"
                animate={{ 
                  textShadow: [
                    "0 0 0px rgba(16, 185, 129, 0)",
                    "0 0 10px rgba(16, 185, 129, 0.3)",
                    "0 0 0px rgba(16, 185, 129, 0)"
                  ]
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                47,000+
                </motion.div>
              <div className="text-white/50 text-sm">Course mappings</div>
              <div className="absolute top-4 right-4 flex items-center space-x-1">
                <motion.div
                  className="w-2 h-2 bg-emerald-400 rounded-full"
                  animate={{ 
                    scale: [1, 1.3, 1],
                    opacity: [0.7, 1, 0.7],
                    boxShadow: [
                      "0 0 0px rgba(16, 185, 129, 0)",
                      "0 0 8px rgba(16, 185, 129, 0.6)",
                      "0 0 0px rgba(16, 185, 129, 0)"
                    ]
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                />
                <span className="text-emerald-400 text-xs font-medium">Live</span>
          </div>
            </motion.div>

          <motion.div
              className="relative p-8 rounded-3xl bg-gradient-to-br from-white/5 to-white/10 border border-white/20 text-center group"
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.2 }}
              whileHover={{ scale: 1.02, borderColor: "rgba(59, 130, 246, 0.3)" }}
            >
              {/* Animated border glow */}
              <motion.div
                className="absolute inset-0 rounded-3xl bg-gradient-to-r from-blue-500/20 via-transparent to-blue-500/20"
                animate={{
                  opacity: [0, 0.5, 0]
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: 1
                }}
              />
              
              {/* Data particles */}
              {[...Array(4)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-1 h-1 bg-blue-400/60 rounded-full"
                  style={{
                    right: `${20 + i * 20}%`,
                    top: `${30 + (i % 2) * 40}%`
                  }}
                  animate={{
                    y: [0, -10, 0],
                    opacity: [0.4, 1, 0.4]
                  }}
                  transition={{
                    duration: 2 + i * 0.3,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: i * 0.5 + 1
                  }}
                />
              ))}
              
              <motion.div 
                className="w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4"
                whileHover={{ rotate: 360 }}
                transition={{ duration: 0.8 }}
              >
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                </svg>
              </motion.div>
              <h3 className="text-xl font-semibold text-white mb-2">UC System</h3>
              <p className="text-white/60 text-sm mb-4">Transfer requirements & deadlines</p>
                        <motion.div
                className="text-3xl font-bold text-blue-400 mb-1"
                animate={{ 
                  textShadow: [
                    "0 0 0px rgba(59, 130, 246, 0)",
                    "0 0 10px rgba(59, 130, 246, 0.3)",
                    "0 0 0px rgba(59, 130, 246, 0)"
                  ]
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: 0.5
                }}
              >
                9
              </motion.div>
              <div className="text-white/50 text-sm">UC campuses</div>
              <div className="absolute top-4 right-4 flex items-center space-x-1">
                <motion.div
                  className="w-2 h-2 bg-blue-400 rounded-full"
                  animate={{ 
                    scale: [1, 1.3, 1],
                    opacity: [0.7, 1, 0.7],
                    boxShadow: [
                      "0 0 0px rgba(59, 130, 246, 0)",
                      "0 0 8px rgba(59, 130, 246, 0.6)",
                      "0 0 0px rgba(59, 130, 246, 0)"
                    ]
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: 0.5
                  }}
                />
                <span className="text-blue-400 text-xs font-medium">Daily</span>
                  </div>
                </motion.div>
            </div>

          {/* Trust Indicators */}
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <div>
              <div className="text-3xl font-bold text-emerald-400 mb-2">99.9%</div>
              <div className="text-white/60 text-sm">Accuracy</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">24/7</div>
              <div className="text-white/60 text-sm">Updates</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-cyan-400 mb-2">116</div>
              <div className="text-white/60 text-sm">CCC Colleges</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-400 mb-2">12K+</div>
              <div className="text-white/60 text-sm">IGETC Courses</div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Final Call to Action */}
      <section className="py-16 sm:py-24 px-4 sm:px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 to-emerald-600/10" />
        
        <div className="relative max-w-4xl mx-auto text-center">
          <motion.h2 
            className="text-3xl sm:text-5xl lg:text-6xl font-bold mb-8"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            Your Transfer Journey{' '}
            <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Starts Now
            </span>
          </motion.h2>
          
          <motion.p 
            className="text-lg lg:text-xl text-white/80 mb-8 max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Stop guessing. Stop stressing. Get your personalized transfer plan and join the hundreds of SMC students who've successfully transferred.
          </motion.p>

          <motion.div
            className="flex items-center justify-center mb-8"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <Link
              href="/chat"
              className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-blue-600 to-emerald-600 rounded-2xl font-bold text-lg text-white shadow-2xl hover:shadow-blue-500/25 transition-all hover:scale-105 group"
            >
              <span className="relative">Get My Transfer Plan</span>
              <svg className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </Link>
          </motion.div>

          <motion.div 
            className="flex items-center justify-center space-x-6 text-white/50 text-sm"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <div className="flex items-center">
              <svg className="w-4 h-4 text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              <span>Always up-to-date</span>
            </div>
            <div className="flex items-center">
              <svg className="w-4 h-4 text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
              </svg>
              <span>Secure & private</span>
            </div>
            <div className="flex items-center">
              <svg className="w-4 h-4 text-purple-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span>Trusted by 1,200+ students</span>
            </div>
          </motion.div>
        </div>
      </section>

       {/* Footer */}
      <footer className="py-24 px-8 bg-slate-950 border-t border-slate-800">
        <div className="max-w-7xl mx-auto">
          {/* Main footer content */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
            {/* Brand column */}
            <div>
              <div className="flex items-center mb-6">
                <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl mr-3 flex items-center justify-center shadow-lg">
                  <span className="text-white font-bold text-lg">A</span>
                </div>
                <span className="text-2xl font-bold text-white">Advisity</span>
              </div>
              <p className="text-slate-400 mb-6 max-w-sm leading-relaxed">
                AI-powered transfer planning for California Community College students. Get clear pathways to UC admission.
              </p>
              
              {/* Trust badges */}
              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center text-emerald-400">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  ASSIST Verified
                </div>
                <div className="flex items-center text-blue-400">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                  </svg>
                  Updated Daily
                </div>
              </div>
            </div>

            {/* Quick Links */}
            <div>
              <h4 className="text-white font-semibold mb-6">Features</h4>
              <ul className="space-y-4">
                <li>
                  <Link href="/chat" className="text-slate-400 hover:text-emerald-400 transition-colors">
                    Course Planning
                  </Link>
                </li>
                <li>
                  <Link href="/chat" className="text-slate-400 hover:text-emerald-400 transition-colors">
                    IGETC Tracking
                  </Link>
                </li>
                <li>
                  <Link href="/chat" className="text-slate-400 hover:text-emerald-400 transition-colors">
                    Admission Odds
                  </Link>
                </li>
                <li>
                  <Link href="/chat" className="text-slate-400 hover:text-emerald-400 transition-colors">
                    UC Requirements
                  </Link>
                </li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="text-white font-semibold mb-6">Resources</h4>
              <ul className="space-y-4">
                <li>
                  <a href="https://assist.org" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-blue-400 transition-colors">
                    ASSIST.org
                  </a>
                </li>
                <li>
                  <a href="https://uc.edu" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-blue-400 transition-colors">
                    UC Transfer Hub
                  </a>
                </li>
                <li>
                  <a href="https://uc.edu/pathways" target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-blue-400 transition-colors">
                    UC Pathways
                  </a>
                </li>
                <li>
                  <Link href="/chat" className="text-slate-400 hover:text-emerald-400 transition-colors">
                    Transfer Deadlines
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom section */}
          <div className="pt-8 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between">
            <div className="text-slate-500 text-sm mb-4 sm:mb-0">
              &copy; 2024 Advisity. Made with ❤️ for CCC students.
            </div>
            
            <div className="flex items-center space-x-6 text-sm">
              <a href="#" className="text-slate-500 hover:text-white transition-colors">Privacy</a>
              <a href="#" className="text-slate-500 hover:text-white transition-colors">Terms</a>
              <a href="#" className="text-slate-500 hover:text-white transition-colors">Contact</a>
              <div className="flex items-center text-slate-500">
                <div className="w-2 h-2 bg-emerald-400 rounded-full mr-2 animate-pulse"></div>
                <span className="text-xs">All systems operational</span>
              </div>
            </div>
          </div>
        </div>
      </footer>


    </div>
  );
};

export default LandingPage; 