import React from 'react'
import { useMissionStore } from '../store'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../components/ui/select'
import { Layers } from 'lucide-react'

interface NoteLevelSelectorProps {
  missionId: string
}

export const NoteLevelSelector: React.FC<NoteLevelSelectorProps> = ({ missionId }) => {
  const { missions, updateMissionResearchParams } = useMissionStore()
  const mission = missions.find(m => m.id === missionId)
  
  // Default to LITERATURE if not set
  const currentLevel = mission?.metadata?.research_params?.note_level || 'LITERATURE'

  const handleValueChange = (value: string) => {
    updateMissionResearchParams(missionId, { note_level: value })
  }

  return (
    <div className="flex items-center space-x-2 px-2 py-0.5 bg-muted/30 rounded-md border border-border/50">
      <div className="flex items-center space-x-1 text-xs text-muted-foreground">
        <Layers className="h-3 w-3" />
        <span className="hidden sm:inline font-medium">Detail:</span>
      </div>
      <Select value={currentLevel} onValueChange={handleValueChange}>
        <SelectTrigger className="h-6 w-[95px] text-xs border-none bg-transparent focus:ring-0 px-1 shadow-none">
          <SelectValue placeholder="Level" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="FLEETING" className="text-xs">
            <span className="font-medium">Fleeting</span>
            <span className="ml-2 text-[10px] text-muted-foreground hidden sm:inline">Raw Facts</span>
          </SelectItem>
          <SelectItem value="LITERATURE" className="text-xs">
            <span className="font-medium">Literature</span>
            <span className="ml-2 text-[10px] text-muted-foreground hidden sm:inline">Synthesis</span>
          </SelectItem>
          <SelectItem value="PERMANENT" className="text-xs">
            <span className="font-medium">Permanent</span>
            <span className="ml-2 text-[10px] text-muted-foreground hidden sm:inline">Deep Insight</span>
          </SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
