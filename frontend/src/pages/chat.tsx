import React, { useState, useEffect } from 'react';

// Add custom styles for schedule building animations
const scheduleAnimationStyles = `
  @keyframes slideInScale {
    0% {
      transform: scale(0) translateY(10px);
      opacity: 0;
    }
    100% {
      transform: scale(1) translateY(0);
      opacity: 1;
    }
  }
  
  @keyframes conflictShake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-2px); }
    75% { transform: translateX(2px); }
  }
  
  @keyframes optimizeFloat {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-3px) rotate(1deg); }
  }
  
  .schedule-appear {
    animation: slideInScale 0.6s ease-out forwards;
  }
  
  .schedule-conflict {
    animation: conflictShake 0.3s ease-in-out infinite;
  }
  
  .schedule-optimize {
    animation: optimizeFloat 1s ease-in-out infinite;
  }
`;

export default function ChatPage() {
  const [currentPage, setCurrentPage] = useState('chat');
  const [messages, setMessages] = useState<{ sender: 'user' | 'bot'; text: string; isSchedule?: boolean; fromCOT?: boolean }[]>([]);
  const [input, setInput] = useState('');
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildingProgress, setBuildingProgress] = useState(0);
  const [buildingPhase, setBuildingPhase] = useState(0);
  const [buildingSteps] = useState([
    { text: "Analyzing your course preferences...", duration: 1200 },
    { text: "Checking class availability...", duration: 1000 },
    { text: "Optimizing time slots...", duration: 800 },
    { text: "Verifying prerequisites...", duration: 900 },
    { text: "Finalizing your schedule...", duration: 700 }
  ]);
  const [animatedCourses, setAnimatedCourses] = useState<any[]>([]);
  const [schedulingAnimation, setSchedulingAnimation] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [currentThought, setCurrentThought] = useState('');
  const [thoughtStep, setThoughtStep] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const [typedText, setTypedText] = useState('');
  const [visibleSteps, setVisibleSteps] = useState(0);

  const [cotCompleted, setCotCompleted] = useState(false);
  const [expandedCotMessages, setExpandedCotMessages] = useState<Set<number>>(new Set());
  
  const toggleCotExpansion = (messageIndex: number) => {
    setExpandedCotMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageIndex)) {
        newSet.delete(messageIndex);
      } else {
        newSet.add(messageIndex);
      }
      return newSet;
    });
  };
  const [allCompletedSteps, setAllCompletedSteps] = useState<Array<{text: string; detail: string}>>([]);

  const thoughtSteps = [
    { 
      text: "Analyzing your query...", 
      detail: "Processing natural language input",
      duration: 1500 
    },
    { 
      text: "Accessing ASSIST database...", 
      detail: "Connecting to UC transfer articulation system",
      duration: 2000 
    },
    { 
      text: "Retrieving course mappings...", 
      detail: "Santa Monica College → UC San Diego pathways",
      duration: 1800 
    },
    { 
      text: "Cross-referencing requirements...", 
      detail: "Validating prerequisites and transfer credits",
      duration: 1600 
    },
    { 
      text: "Analyzing articulation agreements...", 
      detail: "Checking major preparation requirements",
      duration: 1400 
    },
    { 
      text: "Generating recommendations...", 
      detail: "Building personalized transfer pathway",
      duration: 1200 
    }
  ];

  const startChainOfThought = () => {
    setIsThinking(true);
    setThoughtStep(0);
    setVisibleSteps(1); // Start with first step visible
    setCotCompleted(false);
    setAllCompletedSteps([]);
    
    const runThoughtStep = (stepIndex: number) => {
      if (stepIndex >= thoughtSteps.length) {
        // All steps completed - start elegant completion sequence
        setTimeout(() => {
          setIsThinking(false);
          setAllCompletedSteps(thoughtSteps);
          setCotCompleted(true);
          
          setTimeout(() => {
            startTypingResponse();
          }, 500);
        }, 800);
        return;
      }
      
      const step = thoughtSteps[stepIndex];
      setCurrentThought(step.text);
      setThoughtStep(stepIndex);
      setVisibleSteps(stepIndex + 1); // Only show current step, not future ones
      
      setTimeout(() => {
        // Right before moving to next step, reveal it
        if (stepIndex + 1 < thoughtSteps.length) {
          setVisibleSteps(stepIndex + 2);
          setTimeout(() => {
            runThoughtStep(stepIndex + 1);
          }, 200); // Small delay for smooth appearance
        } else {
          runThoughtStep(stepIndex + 1);
        }
      }, step.duration - 200); // Reveal next step 200ms before current completes
    };
    
    runThoughtStep(0);
  };

  const startTypingResponse = () => {
    setIsTyping(true);
    setTypedText('');
    
    const fullResponse = "Based on my analysis of the ASSIST articulation database and UC San Diego transfer requirements, I can help you create an optimal transfer pathway. I've identified key prerequisite courses, analyzed credit transfer patterns, and cross-referenced major preparation requirements to ensure you meet all necessary criteria for successful transfer admission.";
    
    let currentIndex = 0;
    const typingInterval = setInterval(() => {
      if (currentIndex < fullResponse.length) {
        setTypedText(fullResponse.substring(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(typingInterval);
        setTimeout(() => {
          setIsTyping(false);
          setMessages(prev => [...prev, { sender: 'bot', text: fullResponse, fromCOT: true }]);
          setTypedText('');
          setCotCompleted(false); // Reset for next COT
          // Clean up temporary typing COT expansion state
          setExpandedCotMessages(prev => {
            const newSet = new Set(prev);
            newSet.delete(-1);
            return newSet;
          });
        }, 800);
      }
    }, 25);
  };

  const generateScheduleCalendar = () => {
    const timeSlots = [
      '8:00 AM', '9:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', 
      '1:00 PM', '2:00 PM', '3:00 PM', '4:00 PM', '5:00 PM'
    ];
    
    const schedule = {
      'Monday': {
        '8:00 AM': { course: 'MATH 150', title: 'Calculus I', room: 'SCI 201', color: 'bg-blue-500' },
        '10:00 AM': { course: 'ENGL 101', title: 'Composition', room: 'HUM 105', color: 'bg-green-500' },
        '1:00 PM': { course: 'CHEM 210', title: 'General Chemistry', room: 'SCI 315', color: 'bg-purple-500' }
      },
      'Tuesday': {
        '9:00 AM': { course: 'PHYS 220', title: 'Physics I', room: 'SCI 402', color: 'bg-orange-500' },
        '11:00 AM': { course: 'HIST 120', title: 'World History', room: 'HUM 201', color: 'bg-red-500' },
        '2:00 PM': { course: 'PSYC 101', title: 'Intro Psychology', room: 'SOC 110', color: 'bg-cyan-500' }
      },
      'Wednesday': {
        '8:00 AM': { course: 'MATH 150', title: 'Calculus I', room: 'SCI 201', color: 'bg-blue-500' },
        '10:00 AM': { course: 'ENGL 101', title: 'Composition', room: 'HUM 105', color: 'bg-green-500' },
        '1:00 PM': { course: 'CHEM 210', title: 'General Chemistry', room: 'SCI 315', color: 'bg-purple-500' },
        '3:00 PM': { course: 'CHEM 210L', title: 'Chemistry Lab', room: 'SCI 320', color: 'bg-purple-600', duration: 2 }
      },
      'Thursday': {
        '9:00 AM': { course: 'PHYS 220', title: 'Physics I', room: 'SCI 402', color: 'bg-orange-500' },
        '11:00 AM': { course: 'HIST 120', title: 'World History', room: 'HUM 201', color: 'bg-red-500' },
        '2:00 PM': { course: 'PSYC 101', title: 'Intro Psychology', room: 'SOC 110', color: 'bg-cyan-500' }
      },
      'Friday': {
        '8:00 AM': { course: 'MATH 150', title: 'Calculus I', room: 'SCI 201', color: 'bg-blue-500' },
        '10:00 AM': { course: 'ENGL 101', title: 'Composition', room: 'HUM 105', color: 'bg-green-500' },
        '1:00 PM': { course: 'CHEM 210', title: 'General Chemistry', room: 'SCI 315', color: 'bg-purple-500' },
        '2:00 PM': { course: 'PHYS 220L', title: 'Physics Lab', room: 'SCI 410', color: 'bg-orange-600', duration: 2 }
      }
    };

    return { timeSlots, schedule };
  };

  const ScheduleCalendar = ({ preview = false }: { preview?: boolean }) => {
    const { timeSlots, schedule } = generateScheduleCalendar();
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
    const daysFull = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

    return (
      <div className={`bg-gradient-to-br from-zinc-900/95 to-zinc-800/95 backdrop-blur-sm border border-zinc-700/50 rounded-3xl shadow-2xl ${
        preview ? 'p-4' : 'p-8'
      }`}>
        <div className={`flex items-center justify-between ${preview ? 'mb-4' : 'mb-8'}`}>
          <div>
            <h3 className={`font-bold text-white mb-1 ${preview ? 'text-lg' : 'text-2xl'}`}>Fall 2024 Schedule</h3>
            <p className={`text-zinc-400 ${preview ? 'text-xs' : 'text-sm'}`}>Optimized for your academic success</p>
          </div>
          <div className="text-right flex items-center space-x-3">
            <div className={`bg-gradient-to-r from-blue-500/20 to-green-500/20 border border-blue-500/30 rounded-xl ${preview ? 'px-3 py-1' : 'px-4 py-2'}`}>
              <div className={`font-bold text-white ${preview ? 'text-sm' : 'text-lg'}`}>16</div>
              <div className="text-xs text-zinc-300">Total Units</div>
            </div>
            {preview && (
              <button
                onClick={() => setCurrentPage('schedule')}
                className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white text-sm px-4 py-2 rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl"
              >
                View Full Schedule
              </button>
            )}
          </div>
        </div>
        
        {/* Desktop View */}
        <div className="hidden md:block overflow-x-auto">
          <div className={`grid grid-cols-6 min-w-full ${preview ? 'gap-2' : 'gap-3'}`}>
            {/* Header Row */}
            <div className={preview ? 'p-2' : 'p-3'}></div>
            {daysFull.map((day, index) => (
              <div key={day} className={`text-center ${preview ? 'p-2' : 'p-3'}`}>
                <div className={`font-semibold text-white ${preview ? 'text-xs' : 'text-sm'}`}>{days[index]}</div>
                <div className="text-xs text-zinc-400 mt-1">{day.slice(0, 3)} {index + 2}</div>
              </div>
            ))}
            
            {/* Time Slots */}
            {(preview ? timeSlots.slice(0, 6) : timeSlots).map(time => (
              <React.Fragment key={time}>
                <div className={`text-xs text-zinc-400 text-right font-mono ${preview ? 'p-2' : 'p-3'}`}>
                  {time}
                </div>
                {daysFull.map(day => {
                  const course = (schedule as any)[day]?.[time];
                  return (
                    <div key={`${day}-${time}`} className={`p-1 relative ${preview ? 'h-14' : 'h-20'}`}>
                      {course && (
                        <div className={`${course.color} rounded-xl text-white h-full flex flex-col justify-center shadow-lg hover:shadow-xl transition-all duration-300 border border-white/10 backdrop-blur-sm group cursor-pointer ${
                          preview ? 'text-xs p-2' : 'text-xs p-3'
                        }`}>
                          <div className="font-semibold truncate text-white/95 group-hover:text-white transition-colors leading-tight">
                            {course.course}
                          </div>
                          {!preview && (
                            <>
                              <div className="text-xs opacity-80 truncate mt-1 leading-tight">
                                {course.room}
                              </div>
                              {course.title && (
                                <div className="text-xs opacity-70 truncate leading-tight">
                                  {course.title}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Mobile View */}
        <div className={`md:hidden ${preview ? 'space-y-2' : 'space-y-4'}`}>
          {daysFull.map((day, dayIndex) => (
            <div key={day} className={`bg-zinc-800/50 rounded-2xl border border-zinc-700/50 ${preview ? 'p-3' : 'p-4'}`}>
              <h4 className={`font-semibold text-white mb-3 ${preview ? 'text-base' : 'text-lg'}`}>{day}</h4>
              <div className={preview ? 'space-y-1' : 'space-y-2'}>
                {(preview ? timeSlots.slice(0, 6) : timeSlots).map(time => {
                  const course = (schedule as any)[day]?.[time];
                  if (!course) return null;
                  return (
                    <div key={time} className={`${course.color} rounded-xl shadow-lg border border-white/10 ${preview ? 'p-3' : 'p-4'}`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <div className={`font-semibold text-white leading-tight ${preview ? 'text-sm' : ''}`}>{course.course}</div>
                          {!preview && (
                            <div className="text-xs opacity-90 mt-1 leading-tight">{course.title}</div>
                          )}
                        </div>
                        <div className={`text-right opacity-80 ${preview ? 'text-xs' : 'text-xs'}`}>
                          <div className="leading-tight">{time}</div>
                          {!preview && (
                            <div className="leading-tight">{course.room}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        
        {!preview && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gradient-to-r from-zinc-800/60 to-zinc-700/60 backdrop-blur-sm rounded-2xl p-6 border border-zinc-600/30">
              <h4 className="text-lg font-semibold text-white mb-4">Schedule Insights</h4>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-300 text-sm">Study Hours</span>
                  <span className="text-white font-medium">20/week</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-300 text-sm">Free Afternoons</span>
                  <span className="text-green-400 font-medium">Tue, Thu</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-300 text-sm">Lab Sessions</span>
                  <span className="text-blue-400 font-medium">2 sessions</span>
                </div>
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-green-900/30 to-blue-900/30 backdrop-blur-sm rounded-2xl p-6 border border-green-500/20">
              <h4 className="text-lg font-semibold text-white mb-4">Transfer Status</h4>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-bold text-lg">✓</span>
                </div>
                <div>
                  <div className="text-green-400 font-semibold">Transfer Ready</div>
                  <div className="text-zinc-300 text-sm">All requirements met</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const FullSchedulePage = () => {
    return (
      <div className="flex-1 flex flex-col bg-zinc-700">
        {/* Header */}
        <div className="p-6 border-b border-zinc-600">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold text-white mb-2">My Schedule</h2>
              <p className="text-zinc-400">Fall 2024 Academic Calendar</p>
            </div>
            <button
              onClick={() => setCurrentPage('chat')}
              className="bg-zinc-600 hover:bg-zinc-500 text-white px-4 py-2 rounded-xl transition-all duration-300"
            >
              Back to Chat
            </button>
          </div>
        </div>

        {/* Full Schedule Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <ScheduleCalendar preview={false} />
        </div>
      </div>
    );
  };

  const startScheduleBuilding = () => {
    setIsBuilding(true);
    setBuildingProgress(0);
    setBuildingPhase(0);
    setAnimatedCourses([]);
    setSchedulingAnimation('');
    
    const courses = [
      { id: 'math150', name: 'MATH 150', title: 'Calculus I', color: 'bg-blue-500', priority: 1 },
      { id: 'engl101', name: 'ENGL 101', title: 'Composition', color: 'bg-green-500', priority: 2 },
      { id: 'chem210', name: 'CHEM 210', title: 'Gen Chemistry', color: 'bg-purple-500', priority: 3 },
      { id: 'phys220', name: 'PHYS 220', title: 'Physics I', color: 'bg-orange-500', priority: 4 },
      { id: 'hist120', name: 'HIST 120', title: 'World History', color: 'bg-red-500', priority: 5 },
      { id: 'psyc101', name: 'PSYC 101', title: 'Psychology', color: 'bg-cyan-500', priority: 6 }
    ];
    
    const runBuildingPhase = (phaseIndex: number) => {
      if (phaseIndex >= buildingSteps.length) {
        setTimeout(() => {
          setIsBuilding(false);
          setAnimatedCourses([]);
          setMessages(prev => [...prev, { sender: 'bot' as const, text: '', isSchedule: true }]);
        }, 800);
        return;
      }
      
      setBuildingPhase(phaseIndex);
      
      // Phase-specific animations
      if (phaseIndex === 0) {
        // Phase 0: Analyzing preferences - show courses appearing
        setSchedulingAnimation('analyzing');
        courses.forEach((course, index) => {
          setTimeout(() => {
            setAnimatedCourses(prev => [...prev, { ...course, status: 'appearing', position: index }]);
          }, index * 200);
        });
      } else if (phaseIndex === 1) {
        // Phase 1: Checking availability - show conflicts and availability
        setSchedulingAnimation('checking');
        setTimeout(() => {
          setAnimatedCourses(prev => prev.map(course => 
            Math.random() > 0.7 ? { ...course, status: 'conflict' } : { ...course, status: 'available' }
          ));
        }, 300);
      } else if (phaseIndex === 2) {
        // Phase 2: Optimizing - show courses moving around
        setSchedulingAnimation('optimizing');
        const shuffleInterval = setInterval(() => {
          setAnimatedCourses(prev => [...prev].sort(() => Math.random() - 0.5).map((course, index) => ({
            ...course, 
            status: 'moving',
            position: index
          })));
        }, 400);
        setTimeout(() => clearInterval(shuffleInterval), 600);
      } else if (phaseIndex === 3) {
        // Phase 3: Verifying prerequisites - show validation
        setSchedulingAnimation('verifying');
        setTimeout(() => {
          setAnimatedCourses(prev => prev.map(course => ({ ...course, status: 'verified' })));
        }, 300);
      } else if (phaseIndex === 4) {
        // Phase 4: Finalizing - show final placement
        setSchedulingAnimation('finalizing');
        setTimeout(() => {
          setAnimatedCourses(prev => prev.map(course => ({ ...course, status: 'finalized' })));
        }, 200);
      }
      
      const progressPerPhase = 100 / buildingSteps.length;
      const startProgress = phaseIndex * progressPerPhase;
      const endProgress = (phaseIndex + 1) * progressPerPhase;
      
      const duration = buildingSteps[phaseIndex].duration;
      const steps = 30;
      const progressIncrement = (endProgress - startProgress) / steps;
      let currentStep = 0;
      
      const interval = setInterval(() => {
        currentStep++;
        setBuildingProgress(startProgress + (progressIncrement * currentStep));
        
        if (currentStep >= steps) {
          clearInterval(interval);
          setTimeout(() => {
            runBuildingPhase(phaseIndex + 1);
          }, 200);
        }
      }, duration / steps);
    };
    
    runBuildingPhase(0);
  };

  const handleSend = () => {
    if (!input.trim()) return;
    
    const userMessage = { sender: 'user' as const, text: input };
    setMessages(prev => [...prev, userMessage]);
    
    if (input.toLowerCase().includes('schedule')) {
      startScheduleBuilding();
    } else if (input.toLowerCase() === 'cot') {
      startChainOfThought();
    } else {
      const botResponse = { sender: 'bot' as const, text: 'I understand you\'re asking about that topic. Based on your question, I can help you explore course transfer options, academic planning strategies, and admissions requirements. What specific aspect would you like me to focus on? For example, I can help with prerequisite mapping, transfer credit evaluation, or timeline planning for your academic goals.' };
      setMessages(prev => [...prev, botResponse]);
    }
    
    setInput('');
  };

  return (
    <div className="flex h-screen bg-zinc-200 text-white font-sans">
      <style dangerouslySetInnerHTML={{__html: scheduleAnimationStyles}} />
      {/* Sidebar */}
      <div className="w-72 bg-zinc-800 border-r border-zinc-700 flex flex-col">
        <div className="p-6 border-b border-zinc-700">
          <div className="flex items-center">
            <img src="/logo.png" alt="Advisity" className="w-8 h-8 mr-3" />
            <div>
              <h1 className="text-2xl text-white" style={{fontFamily: '"DM Serif Text", Georgia, "Times New Roman", serif', fontWeight: '400', letterSpacing: '0.05em'}}>advisity</h1>
            </div>
          </div>
        </div>
        
        <div className="flex-1 p-6">
          <nav className="space-y-2">
            <button 
              onClick={() => setCurrentPage('chat')}
              className={`flex items-center px-3 py-2 rounded-lg w-full text-left transition-all ${
                currentPage === 'chat' 
                  ? 'bg-zinc-700 text-white border-l-3 border-[#487c5f]' 
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-700'
              }`} 
              style={currentPage === 'chat' ? {borderLeftColor: '#487c5f'} : {}}
            >
              Academic Chat
            </button>
            <button 
              onClick={() => setCurrentPage('schedule')}
              className={`flex items-center px-3 py-2 rounded-lg w-full text-left transition-all ${
                currentPage === 'schedule' 
                  ? 'bg-zinc-700 text-white border-l-3 border-[#487c5f]' 
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-700'
              }`}
              style={currentPage === 'schedule' ? {borderLeftColor: '#487c5f'} : {}}
            >
              Schedule
            </button>
            <a href="#" className="flex items-center px-3 py-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-700 transition-all">
              Applications
            </a>
            <a href="#" className="flex items-center px-3 py-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-700 transition-all">
              Schools
            </a>
          </nav>
        </div>
        
        <div className="p-6 border-t border-zinc-700">
          <button className="w-full px-4 py-2 bg-zinc-700 text-white rounded-lg hover:bg-zinc-600 transition-all font-normal border border-zinc-600">
            Upgrade to Pro
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {currentPage === 'chat' ? (
        <div className="flex flex-col flex-1 bg-zinc-700">
        {/* Header */}
        <div className="p-6">
        </div>

        {/* Content Area - Conditional Layout */}
        {messages.length === 0 ? (
          /* Empty State - Centered Input */
          <div className="flex-1 flex flex-col items-center justify-center p-6">
            <div className="text-center mb-8">
              <h3 className="text-2xl font-extralight text-white mb-2">How can I help with your application process?</h3>
              <p className="text-zinc-400 text-sm">Ask about courses, transfers, requirements, or planning</p>
            </div>
            
            <div className="w-full max-w-2xl">
              <div className="flex items-center gap-3 bg-zinc-600 border border-zinc-500 rounded-2xl p-3 shadow-lg">
                <input
                  className="flex-1 bg-transparent text-white placeholder:text-zinc-400 outline-none"
                  placeholder="Ask about courses, transfers, planning..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button
                  onClick={handleSend}
                  className="text-white px-6 py-2 rounded-xl hover:opacity-80 transition-all font-normal"
                  style={{backgroundColor: '#487c5f'}}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Normal Chat Layout */
          <>
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((msg, i) => (
                <div key={i}>
                  {msg.sender === 'user' ? (
                    <div className="flex justify-end mb-4">
                      <div className="max-w-[80%] px-4 py-3 rounded-2xl bg-white text-black font-normal">
                        {msg.text}
                      </div>
                    </div>
                  ) : (
                    <div className="mb-6">
                      {/* Show completed COT summary before the bot response */}
                      {msg.fromCOT && (
                        <div className="mb-6">
                          <div className="bg-gradient-to-r from-green-900/20 to-green-800/20 border border-green-600/30 rounded-2xl p-4 shadow-lg transition-all duration-500 ease-out">
                            <button
                              onClick={() => toggleCotExpansion(i)}
                              className="flex items-center justify-between w-full text-left hover:bg-green-500/10 rounded-lg p-2 transition-all duration-300"
                            >
                              <div className="flex items-center space-x-3">
                                <div className="w-4 h-4 rounded-full bg-green-400"></div>
                                <span className="text-green-300 font-medium">Chain of Thought Completed</span>
                                <span className="text-green-400 text-sm">({allCompletedSteps.length} steps)</span>
                              </div>
                              <div className={`text-green-400 transition-transform duration-300 ${expandedCotMessages.has(i) ? 'rotate-180' : ''}`}>
                                ▼
                              </div>
                            </button>
                            
                            {expandedCotMessages.has(i) && (
                              <div className="mt-4 space-y-2 transition-all duration-300 ease-out">
                                {allCompletedSteps.map((step, index) => (
                                  <div 
                                    key={`summary-${index}`}
                                    className="flex items-center space-x-3 p-2 rounded-lg bg-green-500/5 border border-green-500/10"
                                  >
                                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                                    <div className="flex-1">
                                      <div className="text-sm font-medium text-green-300">
                                        {step.text}
                                      </div>
                                      <div className="text-xs text-green-400 opacity-80">
                                        {step.detail}
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {msg.isSchedule ? (
                        <ScheduleCalendar preview={true} />
                      ) : (
                        <div className="text-white leading-relaxed whitespace-pre-line">
                          {msg.text}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              
              {isBuilding && (
                <div className="mb-6">
                  <div className="bg-gradient-to-br from-zinc-800/90 to-zinc-900/90 border border-zinc-600/50 rounded-3xl p-6 shadow-2xl backdrop-blur-sm">
                    <div className="flex items-center space-x-4 mb-6">
                      <div className="relative">
                        <div className="w-6 h-6 border-3 border-zinc-400 border-t-transparent rounded-full animate-spin"></div>
                        <div className="absolute inset-0 w-6 h-6 border-3 border-transparent border-t-blue-400 rounded-full animate-spin" style={{animationDirection: 'reverse', animationDuration: '0.8s'}}></div>
                      </div>
                      <div>
                        <div className="text-white font-medium text-lg">Building Your Schedule</div>
                        <div className="text-zinc-300 text-sm">Optimizing for your academic success</div>
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-300 text-sm font-medium">{buildingSteps[buildingPhase]?.text}</span>
                        <span className="text-zinc-400 text-xs">{Math.round(buildingProgress)}%</span>
                      </div>
                      
                      <div className="relative">
                        <div className="w-full bg-zinc-700 rounded-full h-2 overflow-hidden">
                          <div 
                            className="h-full rounded-full transition-all duration-200 ease-out bg-gradient-to-r from-blue-500 to-green-500 shadow-lg"
                            style={{ width: `${buildingProgress}%` }}
                          ></div>
                        </div>
                        <div 
                          className="absolute top-0 h-2 w-8 bg-gradient-to-r from-transparent via-white/30 to-transparent rounded-full transition-all duration-200 ease-out animate-pulse"
                          style={{ left: `${Math.max(0, buildingProgress - 8)}%` }}
                        ></div>
                      </div>
                      
                      <div className="grid grid-cols-5 gap-2 mt-4">
                        {buildingSteps.map((step, index) => (
                          <div key={index} className="flex flex-col items-center space-y-1">
                            <div className={`w-2 h-2 rounded-full transition-all duration-300 ${
                              index <= buildingPhase 
                                ? 'bg-gradient-to-r from-blue-400 to-green-400 shadow-lg' 
                                : 'bg-zinc-600'
                            }`}></div>
                            <div className={`text-xs text-center transition-colors duration-300 ${
                              index === buildingPhase 
                                ? 'text-blue-300' 
                                : index < buildingPhase 
                                  ? 'text-green-300' 
                                  : 'text-zinc-500'
                            }`}>
                              {step.text.split(' ')[0]}
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      {/* Live Schedule Building Animation */}
                      <div className="mt-6 p-4 bg-zinc-800/30 rounded-xl border border-zinc-700/50">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-sm font-medium text-zinc-300">Schedule Preview</h4>
                          <div className={`text-xs px-2 py-1 rounded-full ${
                            schedulingAnimation === 'analyzing' ? 'bg-blue-500/20 text-blue-300' :
                            schedulingAnimation === 'checking' ? 'bg-yellow-500/20 text-yellow-300' :
                            schedulingAnimation === 'optimizing' ? 'bg-purple-500/20 text-purple-300' :
                            schedulingAnimation === 'verifying' ? 'bg-green-500/20 text-green-300' :
                            schedulingAnimation === 'finalizing' ? 'bg-emerald-500/20 text-emerald-300' :
                            'bg-zinc-500/20 text-zinc-400'
                          }`}>
                            {schedulingAnimation || 'preparing'}
                          </div>
                        </div>
                        
                        {/* Mini Schedule Grid */}
                        <div className="grid grid-cols-6 gap-1 text-xs">
                          {/* Header */}
                          <div className="text-zinc-500 text-center py-1"></div>
                          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(day => (
                            <div key={day} className="text-zinc-400 text-center py-1 font-mono">
                              {day}
                            </div>
                          ))}
                          
                                                     {/* Time Slots */}
                           {['8AM', '10AM', '12PM', '2PM'].map((time, timeIndex) => (
                             <React.Fragment key={time}>
                               <div className="text-zinc-500 text-right py-3 pr-1 font-mono">
                                 {time}
                               </div>
                               {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map((day, dayIndex) => {
                                 const slotIndex = timeIndex * 5 + dayIndex;
                                 const course = animatedCourses[slotIndex % animatedCourses.length];
                                 
                                 return (
                                   <div key={`${day}-${time}`} className="h-12 relative">
                                     {course && (
                                       <div className={`absolute inset-0 ${
                                         course.status === 'conflict' ? 'bg-red-500' : course.color
                                       } rounded text-white text-xs p-2 flex flex-col items-center justify-center font-medium transition-all duration-300 ${
                                         course.status === 'appearing' ? 'schedule-appear' :
                                         course.status === 'conflict' ? 'schedule-conflict scale-105' :
                                         course.status === 'available' ? 'scale-100 opacity-100' :
                                         course.status === 'moving' ? 'schedule-optimize' :
                                         course.status === 'verified' ? 'scale-100 opacity-100 ring-2 ring-green-400 shadow-lg' :
                                         course.status === 'finalized' ? 'scale-100 opacity-100 shadow-xl ring-1 ring-white/20' :
                                         'scale-100 opacity-100'
                                       }`}
                                       style={{
                                         animationDelay: course.status === 'appearing' ? `${(course.position || 0) * 150}ms` : undefined
                                       }}
                                       >
                                         <div className="text-center leading-tight">
                                           <div className="font-semibold text-xs">
                                             {course.name}
                                           </div>
                                           <div className="text-xs opacity-90 mt-0.5">
                                             {course.title.split(' ').slice(0, 2).join(' ')}
                                           </div>
                                         </div>
                                         {course.status === 'verified' && (
                                           <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full flex items-center justify-center">
                                             <span className="text-white text-xs">✓</span>
                                           </span>
                                         )}
                                         {course.status === 'conflict' && (
                                           <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full flex items-center justify-center">
                                             <span className="text-white text-xs">!</span>
                                           </span>
                                         )}
                                       </div>
                                     )}
                                   </div>
                                 );
                               })}
                             </React.Fragment>
                           ))}
                        </div>
                        
                        {/* AI Actions Display */}
                        <div className="mt-3 flex items-center space-x-2 text-xs">
                          <div className="flex space-x-1">
                            <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
                            <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                            <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                          </div>
                          <span className="text-zinc-400">
                            {schedulingAnimation === 'analyzing' ? 'Scanning course catalog...' :
                             schedulingAnimation === 'checking' ? 'Resolving time conflicts...' :
                             schedulingAnimation === 'optimizing' ? 'Balancing workload distribution...' :
                             schedulingAnimation === 'verifying' ? 'Validating prerequisites...' :
                             schedulingAnimation === 'finalizing' ? 'Locking in optimal schedule...' :
                             'Initializing smart scheduler...'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {isThinking && (
                <div className="mb-6">
                  <div className="bg-gradient-to-r from-zinc-800 to-zinc-700 border border-zinc-600 rounded-2xl p-6 shadow-xl transition-all duration-500 ease-out">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-white font-medium">Chain of Thought Process</span>
                    </div>
                    
                    <div className="space-y-3">
                      {thoughtSteps.slice(0, visibleSteps).map((step, index) => (
                        <div 
                          key={index}
                          className={`flex items-center space-x-4 p-3 rounded-lg transition-all duration-700 ease-out transform ${
                            index === thoughtStep 
                              ? 'bg-blue-500/20 border border-blue-500/30 scale-105' 
                              : index < thoughtStep 
                                ? 'bg-green-500/10 border border-green-500/20' 
                                : 'bg-zinc-700/50 border border-zinc-600/30'
                          } ${index === visibleSteps - 1 && index !== 0 && index !== thoughtStep ? 'opacity-0' : ''}`}
                          style={{
                            animation: index === visibleSteps - 1 && index !== 0 && index !== thoughtStep
                              ? 'slideIn 0.5s ease-out forwards' 
                              : 'none'
                          }}
                        >
                          <div className={`w-3 h-3 rounded-full transition-all duration-500 ${
                            index === thoughtStep 
                              ? 'bg-blue-400 animate-pulse' 
                              : index < thoughtStep 
                                ? 'bg-green-400' 
                                : 'bg-zinc-500'
                          }`}>
                          </div>
                          <div className="flex-1">
                            <div className={`font-medium transition-colors duration-500 ${
                              index === thoughtStep 
                                ? 'text-blue-300' 
                                : index < thoughtStep 
                                  ? 'text-green-300' 
                                  : 'text-zinc-400'
                            }`}>
                              {step.text}
                            </div>
                            <div className={`text-sm transition-colors duration-500 ${
                              index === thoughtStep 
                                ? 'text-blue-400' 
                                : index < thoughtStep 
                                  ? 'text-green-400' 
                                  : 'text-zinc-500'
                            }`}>
                              {step.detail}
                            </div>
                          </div>
                          {index === thoughtStep && (
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce transition-all duration-300"></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce transition-all duration-300" style={{animationDelay: '0.1s'}}></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce transition-all duration-300" style={{animationDelay: '0.2s'}}></div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              

              
              {isTyping && (
                <>
                  {/* Show completed COT summary above typing when it's a COT response */}
                  {cotCompleted && (
                    <div className="mb-6">
                      <div className="bg-gradient-to-r from-green-900/20 to-green-800/20 border border-green-600/30 rounded-2xl p-4 shadow-lg transition-all duration-500 ease-out">
                                                 <button
                           onClick={() => toggleCotExpansion(-1)}
                           className="flex items-center justify-between w-full text-left hover:bg-green-500/10 rounded-lg p-2 transition-all duration-300"
                         >
                           <div className="flex items-center space-x-3">
                             <div className="w-4 h-4 rounded-full bg-green-400"></div>
                             <span className="text-green-300 font-medium">Chain of Thought Completed</span>
                             <span className="text-green-400 text-sm">({allCompletedSteps.length} steps)</span>
                           </div>
                           <div className={`text-green-400 transition-transform duration-300 ${expandedCotMessages.has(-1) ? 'rotate-180' : ''}`}>
                             ▼
                           </div>
                         </button>
                         
                         {expandedCotMessages.has(-1) && (
                          <div className="mt-4 space-y-2 transition-all duration-300 ease-out">
                            {allCompletedSteps.map((step, index) => (
                              <div 
                                key={`summary-${index}`}
                                className="flex items-center space-x-3 p-2 rounded-lg bg-green-500/5 border border-green-500/10"
                              >
                                <div className="w-2 h-2 rounded-full bg-green-400"></div>
                                <div className="flex-1">
                                  <div className="text-sm font-medium text-green-300">
                                    {step.text}
                                  </div>
                                  <div className="text-xs text-green-400 opacity-80">
                                    {step.detail}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  <div className="mb-6">
                    <div className="text-white leading-relaxed">
                      {typedText}<span className="animate-pulse">|</span>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Input */}
            <div className="p-6 bg-zinc-700">
              <div className="flex items-center gap-3 bg-zinc-600 border border-zinc-500 rounded-2xl p-3 shadow-lg">
                <input
                  className="flex-1 bg-transparent text-white placeholder:text-zinc-400 outline-none"
                  placeholder="Ask about courses, transfers, planning..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button
                  onClick={handleSend}
                  className="text-white px-6 py-2 rounded-xl hover:opacity-80 transition-all font-normal"
                  style={{backgroundColor: '#487c5f'}}
                >
                  Send
                </button>
              </div>
            </div>
          </>
        )}
        </div>
      ) : (
        <FullSchedulePage />
      )}
    </div>
  );
}
