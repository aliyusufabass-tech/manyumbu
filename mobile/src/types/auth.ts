export type ApiResponse<T> = {
  success: boolean;
  message: string;
  data: T;
};

export type ManyumbuUser = {
  phone_number: string;
  email: string;
  username: string;
  full_name: string;
  is_email_verified: boolean;
  is_active: boolean;
};

export type AuthTokens = {
  access: string;
  refresh: string;
};
