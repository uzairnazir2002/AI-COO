import { Upload } from "lucide-react";

import { WizardStepper } from "@/components/safety/wizard-stepper";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { csvFields, type CsvMapping } from "@/features/transactions/services/csv";
import type { ImportMappingProfile } from "@/types/domain";

type PreviewRow = Record<string, string>;

export function TransactionsImportDialog({
  open,
  onOpenChange,
  csvStep,
  onFileSelected,
  csvHeaders,
  selectedProfileId,
  onSelectProfile,
  profiles,
  profileName,
  setProfileName,
  profileShared,
  setProfileShared,
  onDeleteProfile,
  onSaveProfile,
  saveProfilePending,
  deleteProfilePending,
  mapping,
  setMapping,
  requiredMissing,
  selectedProfileExists,
  previewRows,
  csvPreview,
  localDupes,
  csvBusy,
  onPreview,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  csvStep: number;
  onFileSelected: (file: File | null) => Promise<void>;
  csvHeaders: string[];
  selectedProfileId: string;
  onSelectProfile: (value: string) => void;
  profiles: ImportMappingProfile[];
  profileName: string;
  setProfileName: (value: string) => void;
  profileShared: boolean;
  setProfileShared: (value: boolean) => void;
  onDeleteProfile: () => Promise<void>;
  onSaveProfile: () => Promise<void>;
  saveProfilePending: boolean;
  deleteProfilePending: boolean;
  mapping: CsvMapping;
  setMapping: (next: CsvMapping) => void;
  requiredMissing: string[];
  selectedProfileExists: boolean;
  previewRows: PreviewRow[];
  csvPreview: { rows: number; detected_duplicates: number } | null;
  localDupes: number;
  csvBusy: boolean;
  onPreview: () => Promise<void>;
  onConfirm: () => Promise<void>;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button id="import" variant="outline">
          <Upload className="mr-2 h-4 w-4" />
          Import CSV
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>CSV import wizard</DialogTitle>
          <DialogDescription>Upload, map columns, preview, detect duplicates, and confirm without leaving the page.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <WizardStepper
            currentStep={csvStep}
            steps={[
              { id: "upload", label: "Upload" },
              { id: "map", label: "Map" },
              { id: "validate", label: "Validate" },
              { id: "commit", label: "Commit" },
            ]}
          />
          <div className="rounded-xl border border-border/70 bg-card/70 p-3 text-sm" data-testid="csv-step-status">
            {csvStep === 1 ? (
              <p>Step 1 - Upload: Select a CSV file to start import mapping and validation.</p>
            ) : null}
            {csvStep === 2 ? (
              <p>
                Step 2 - Map: Resolve required mappings before preview.{" "}
                {requiredMissing.length > 0 ? `Missing: ${requiredMissing.join(", ")}.` : "All required mappings are present."}
              </p>
            ) : null}
            {csvStep === 3 ? (
              <p>Step 3 - Validate: Review duplicates and row issues before committing import.</p>
            ) : null}
            {csvStep === 4 ? (
              <p>Step 4 - Commit: Preview is complete. Confirm import to write rows and queue alert refresh.</p>
            ) : null}
          </div>
          <input data-testid="csv-file-input" type="file" accept=".csv" onChange={(event) => void onFileSelected(event.target.files?.[0] ?? null)} />
          {csvHeaders.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
              <div className="space-y-3">
                <div className="rounded-xl border border-border/70 p-3">
                  <p className="text-sm font-medium">Saved profiles</p>
                  <div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto_auto]">
                    <Select
                      value={selectedProfileId || "__none__"}
                      onValueChange={onSelectProfile}
                    >
                      <SelectTrigger><SelectValue placeholder="Use saved profile" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">No profile</SelectItem>
                        {profiles.map((profile) => (
                          <SelectItem key={profile.id} value={profile.id}>
                            {profile.name}{profile.user_id === null ? " (shared)" : ""}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      disabled={!selectedProfileId || deleteProfilePending}
                      onClick={() => void onDeleteProfile()}
                    >
                      Delete
                    </Button>
                  </div>
                  <div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto_auto]">
                    <Input
                      placeholder="Profile name"
                      value={profileName}
                      onChange={(event) => setProfileName(event.target.value)}
                    />
                    <Select value={profileShared ? "shared" : "personal"} onValueChange={(value) => setProfileShared(value === "shared")}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="personal">Personal</SelectItem>
                        <SelectItem value="shared">Shared</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      disabled={profileName.trim().length === 0 || requiredMissing.length > 0 || saveProfilePending}
                      onClick={() => void onSaveProfile()}
                    >
                      {selectedProfileExists ? "Update profile" : "Save profile"}
                    </Button>
                  </div>
                </div>
                <p className="text-sm font-medium">Column mapping</p>
                {csvFields.map((field) => (
                  <div key={field.key} className="space-y-1">
                    <p className="text-xs text-muted-foreground">{field.label} {field.required ? "*" : "(optional)"}</p>
                    <Select
                      value={mapping[field.key] || "__none__"}
                      onValueChange={(value) => setMapping({ ...mapping, [field.key]: value === "__none__" ? "" : value })}
                    >
                      <SelectTrigger data-testid={`csv-map-${field.key}`}><SelectValue placeholder={`Select ${field.label} column`} /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">Not mapped</SelectItem>
                        {csvHeaders.map((header) => <SelectItem key={`${field.key}-${header}`} value={header}>{header}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
                {requiredMissing.length > 0 ? <InlineErrorBanner message={`Missing required mappings: ${requiredMissing.join(", ")}`} /> : null}
                <div
                  data-testid="csv-action-footer"
                  className="sticky bottom-0 z-20 -mx-3 mt-2 space-y-2 border-t border-border/70 bg-background/95 px-3 pb-1 pt-3 backdrop-blur"
                >
                  <p className="text-xs text-muted-foreground">
                    Validation summary: {requiredMissing.length > 0 ? `Missing ${requiredMissing.join(", ")}` : "All required fields mapped"}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      data-testid="csv-preview-button"
                      variant="outline"
                      disabled={requiredMissing.length > 0 || csvBusy}
                      onClick={() => void onPreview()}
                    >
                      Preview Import
                    </Button>
                    <Button
                      data-testid="csv-confirm-button"
                      disabled={requiredMissing.length > 0 || csvBusy}
                      onClick={() => void onConfirm()}
                    >
                      Confirm Import
                    </Button>
                  </div>
                  {csvPreview ? <p className="text-sm text-muted-foreground">Rows: {csvPreview.rows} | Duplicates detected by backend: {csvPreview.detected_duplicates}</p> : null}
                  <p className="text-sm text-muted-foreground">Local duplicate hints: {localDupes}</p>
                </div>
              </div>
              <div className="space-y-3">
                <p className="text-sm font-medium">Preview</p>
                <div className="max-h-[420px] overflow-auto rounded-2xl border border-border">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-muted">
                      <tr>
                        {csvFields.map((field) => <th key={field.key} className="px-2 py-2 text-left">{field.label}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRows.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          {csvFields.map((field) => <td key={`${idx}-${field.key}`} className="px-2 py-2">{row[field.key]}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
