export type UserResponse = {
  id: number;
  email: string;
  full_name?: string | null;
  company?: string | null;
  role?: string | null;
  description?: string | null;
};

export type TokenPairResponse = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  user: UserResponse;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = LoginRequest;

export type RefreshTokenRequest = {
  refresh_token: string;
};

export type UserUpdateRequest = {
  full_name?: string | null;
  company?: string | null;
  role?: string | null;
  description?: string | null;
};

export type ArtifactType = "source_obj" | "render" | "collage" | "generated_json";

export type ArtifactResponse = {
  id: number;
  type: ArtifactType;
  file_name: string;
  content_type: string;
  size_bytes: number | null;
  checksum: string | null;
  meta_json: Record<string, unknown> | null;
  download_url?: string | null;
  created_at: string;
};

export type RunStatus =
  | "created"
  | "source_uploaded"
  | "rendering"
  | "rendered"
  | "collages_ready"
  | "generating_json"
  | "completed"
  | "failed";

export type RunEventResponse = {
  id: number;
  event_type: string;
  payload_json: Record<string, unknown> | null;
  created_at: string;
};

export type GenerationStatus = "pending" | "running" | "succeeded" | "failed";

export type GenerationResponse = {
  id: number;
  input_collage_artifact_id: number | null;
  output_artifact_id: number | null;
  provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  status: GenerationStatus;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
};

export type RunResponse = {
  id: number;
  user_id: number;
  name: string | null;
  status: RunStatus;
  source_artifact_id: number | null;
  selected_collage_artifact_id: number | null;
  latest_generation_id: number | null;
  created_at: string;
  updated_at: string;
  artifacts: ArtifactResponse[];
  events: RunEventResponse[];
  generations: GenerationResponse[];
};

export type RunCreateRequest = {
  name?: string | null;
};

export type CollageGenerateRequest = {
  counts?: number[];
  selected_count?: number | null;
};

export type CollageSelectRequest = {
  collage_artifact_id: number;
};

export type GenerationCreateRequest = {
  provider?: string;
  model_name?: string;
  prompt_version?: string;
};
