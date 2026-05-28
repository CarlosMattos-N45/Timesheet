import { describe, it, expect, beforeEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { postLogin, postRefresh, postLogout } from "@/api/auth";

const mock = new MockAdapter(api);

describe("api/auth", () => {
  beforeEach(() => {
    mock.reset();
    sessionStorage.clear();
  });

  it("postLogin retorna LoginResponse com campos corretos", async () => {
    mock.onPost("/api/v1/auth/login").reply(200, {
      access_token: "atok",
      refresh_token: "rtok",
      terceiro_id: "uuid",
      expires_in: 900,
    });
    const r = await postLogin("a@b.com", "s3nh4");
    expect(r.access_token).toBe("atok");
    expect(r.terceiro_id).toBe("uuid");
    expect(r.expires_in).toBe(900);
  });

  it("postRefresh retorna novos tokens", async () => {
    mock.onPost("/api/v1/auth/refresh").reply(200, {
      access_token: "novo-atok",
      refresh_token: "novo-rtok",
      expires_in: 900,
    });
    const r = await postRefresh("meu-rtok");
    expect(r.access_token).toBe("novo-atok");
    expect(r.refresh_token).toBe("novo-rtok");
  });

  it("postLogout chama o endpoint correto", async () => {
    mock.onPost("/api/v1/auth/logout").reply(204);
    await expect(postLogout("meu-rtok")).resolves.toBeUndefined();
  });
});
