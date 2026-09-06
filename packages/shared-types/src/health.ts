/**
 * Response payload for the API health check endpoint.
 */
export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}
