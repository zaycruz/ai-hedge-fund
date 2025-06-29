import React, { useState, useEffect } from 'react';
import { Handle, Position } from 'reactflow';
import { NodeShell } from './node-shell';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { Loader2, Settings, Plus, Play } from 'lucide-react';

interface CustomAgentNodeProps {
  data: {
    name: string;
    description?: string;
    model?: string;
    tools?: string[];
    systemPrompt?: string;
    isNew?: boolean;
    onUpdate?: (data: any) => void;
  };
  id: string;
}

interface ToolInfo {
  name: string;
  description: string;
  category: string;
  parameters: any[];
  enabled: boolean;
}

export const CustomAgentNode: React.FC<CustomAgentNodeProps> = ({ data, id }) => {
  const [isConfiguring, setIsConfiguring] = useState(data.isNew || false);
  const [availableTools, setAvailableTools] = useState<Record<string, ToolInfo[]>>({});
  const [selectedTools, setSelectedTools] = useState<string[]>(data.tools || []);
  const [agentName, setAgentName] = useState(data.name || 'Custom Agent');
  const [agentDescription, setAgentDescription] = useState(data.description || '');
  const [systemPrompt, setSystemPrompt] = useState(data.systemPrompt || '');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchAvailableTools();
  }, []);

  const fetchAvailableTools = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/tools/categories');
      if (!response.ok) throw new Error('Failed to fetch tools');
      const tools = await response.json();
      setAvailableTools(tools);
    } catch (error) {
      console.error('Error fetching tools:', error);
      toast.error('Failed to load available tools');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToolToggle = (toolName: string) => {
    setSelectedTools(prev => 
      prev.includes(toolName) 
        ? prev.filter(t => t !== toolName)
        : [...prev, toolName]
    );
  };

  const handleSave = async () => {
    if (!agentName.trim()) {
      toast.error('Agent name is required');
      return;
    }

    try {
      setIsSaving(true);
      
      const agentData = {
        name: agentName,
        description: agentDescription,
        model: data.model || 'gpt-4o',
        tools: selectedTools,
        system_prompt: systemPrompt
      };

      // Create or update the agent
      const response = await fetch('/api/tools/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData)
      });

      if (!response.ok) throw new Error('Failed to save agent');
      
      const result = await response.json();
      
      // Update the node data
      if (data.onUpdate) {
        data.onUpdate({
          ...data,
          ...agentData,
          isNew: false
        });
      }
      
      setIsConfiguring(false);
      toast.success('Agent saved successfully');
    } catch (error) {
      console.error('Error saving agent:', error);
      toast.error('Failed to save agent');
    } finally {
      setIsSaving(false);
    }
  };

  const runAnalysis = async () => {
    try {
      setIsLoading(true);
      
      // For demo purposes, using dummy data
      const analysisRequest = {
        agent_name: agentName,
        market_data: {
          'AAPL': { price: 185.50, change: 1.2 },
          'GOOGL': { price: 142.30, change: -0.5 }
        },
        news_summary: 'Market showing mixed signals...',
        portfolio: {
          cash: 100000,
          positions: {}
        }
      };

      const response = await fetch(`/api/tools/agents/${agentName}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(analysisRequest)
      });

      if (!response.ok) throw new Error('Failed to run analysis');
      
      const result = await response.json();
      toast.success('Analysis completed');
      console.log('Analysis result:', result);
    } catch (error) {
      console.error('Error running analysis:', error);
      toast.error('Failed to run analysis');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <NodeShell 
      title={agentName}
      nodeType="custom-agent"
      status={isLoading ? 'processing' : 'idle'}
      statusMessage={isLoading ? 'Running...' : undefined}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#555' }}
      />
      
      <div className="p-4 min-w-[300px]">
        {!isConfiguring ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{agentDescription || 'Custom agent'}</p>
            
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">Tools:</div>
              <div className="flex flex-wrap gap-1">
                {selectedTools.length > 0 ? (
                  selectedTools.map(tool => (
                    <Badge key={tool} variant="secondary" className="text-xs">
                      {tool}
                    </Badge>
                  ))
                ) : (
                  <span className="text-xs text-muted-foreground">No tools selected</span>
                )}
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsConfiguring(true)}
                disabled={isLoading}
              >
                <Settings className="w-4 h-4 mr-1" />
                Configure
              </Button>
              
              <Button
                size="sm"
                onClick={runAnalysis}
                disabled={isLoading || selectedTools.length === 0}
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-1" />
                )}
                Run
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Agent Name</label>
              <Input
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="Enter agent name"
                className="mt-1"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">Description</label>
              <Input
                value={agentDescription}
                onChange={(e) => setAgentDescription(e.target.value)}
                placeholder="Enter agent description"
                className="mt-1"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">System Prompt</label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Enter custom system prompt (optional)"
                className="mt-1 w-full p-2 text-sm border rounded-md resize-none"
                rows={3}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Select Tools</label>
              <ScrollArea className="h-[200px] border rounded-md p-2">
                {isLoading ? (
                  <div className="flex justify-center items-center h-full">
                    <Loader2 className="w-6 h-6 animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(availableTools).map(([category, tools]) => (
                      <div key={category} className="space-y-2">
                        <h4 className="text-xs font-semibold text-muted-foreground uppercase">
                          {category.replace(/_/g, ' ')}
                        </h4>
                        <div className="space-y-1">
                          {tools.map((tool) => (
                            <div key={tool.name} className="flex items-start space-x-2">
                              <Checkbox
                                checked={selectedTools.includes(tool.name)}
                                onCheckedChange={() => handleToolToggle(tool.name)}
                                id={tool.name}
                              />
                              <label
                                htmlFor={tool.name}
                                className="text-xs cursor-pointer flex-1"
                              >
                                <div className="font-medium">{tool.name}</div>
                                <div className="text-muted-foreground">{tool.description}</div>
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </div>
            
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsConfiguring(false)}
                disabled={isSaving}
              >
                Cancel
              </Button>
              
              <Button
                size="sm"
                onClick={handleSave}
                disabled={isSaving || !agentName.trim()}
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  'Save Agent'
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#555' }}
      />
    </NodeShell>
  );
};