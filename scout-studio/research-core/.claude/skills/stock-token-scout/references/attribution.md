# Mô hình attribution danh tính

Ví deployer, ví creator, pool, lệnh chuyển là **dữ kiện on-chain**. Câu "`0x123...` là @FounderXYZ" là **attribution off-chain** và chỉ đúng khi có cầu nối bằng chứng. AI không được biến suy luận thành dữ kiện.

## Ba đối tượng

| Subject | Câu hỏi |
|---|---|
| `project` | Tài khoản X / website này có đúng là của hợp đồng này không? |
| `creator` | Người này có đúng là người tạo/xây dự án không? |
| `wallet` | Ví này có đúng là của người/đội này không? |

## Loại cầu nối và độ mạnh

Ghi bằng `ledger.py bridge add --subject ... --entity ... --type ... --url ...`. Script từ chối loại không có trong danh sách, và từ chối hẳn `wallet_relationship`.

**project**

| Loại | Độ mạnh | Khi nào dùng |
|---|---|---|
| `website_links_contract` | Mạnh | Website chính thức ghi đúng địa chỉ hợp đồng (script `page --official` tự ghi) |
| `x_links_contract` | Mạnh | Tài khoản X của dự án đăng địa chỉ hợp đồng |
| `launchpad_profile` | Mạnh | Trang token trên launchpad liên kết tới tài khoản/website |
| `x_links_website`, `website_links_x` | Trung bình | Hai chiều liên kết giữa X và website |
| `dex_profile_links` | Trung bình | Hồ sơ trên DexScreener/GeckoTerminal ghi link |
| `fomo_metadata`, `third_party_mention` | Yếu | App tổng hợp hoặc bên thứ ba nhắc |
| `contradiction` | Mâu thuẫn | Hai nguồn chính thức trỏ về hai địa chỉ khác nhau |

**creator**

| Loại | Độ mạnh |
|---|---|
| `signed_message` | Xác minh bằng mật mã |
| `creator_self_claim_with_contract`, `launchpad_creator_profile` | Mạnh (phía creator) |
| `project_names_creator`, `website_names_creator` | Mạnh (phía dự án) |
| `creator_self_claim` (không kèm địa chỉ) | Trung bình |
| `project_reposts_creator`, `third_party_mention` | Yếu |
| `contradiction` | Mâu thuẫn |

**wallet**

| Loại | Độ mạnh |
|---|---|
| `signed_message` | Xác minh bằng mật mã |
| `launchpad_creator_profile`, `public_wallet_disclosure_repeated` | Mạnh |
| `single_wallet_disclosure` | Trung bình |
| `contradiction` | Mâu thuẫn |

## Luật tính mức (trong `ledger.py`, không sửa bằng lời văn)

- Có `contradiction` → `CONFLICT`.
- Có chữ ký ví → `VERIFIED_OFFCHAIN`.
- **project:** hai kênh chính thức độc lập (khác domain) cùng trỏ về hợp đồng → `VERIFIED_OFFCHAIN`; một kênh mạnh hoặc hai kênh trung bình → `LIKELY`; còn lại `UNCONFIRMED`.
- **creator:** cần **cả phía creator** (tự nhận kèm địa chỉ, hoặc hồ sơ creator trên launchpad) **và phía dự án** (dự án/website nêu tên) → `VERIFIED_OFFCHAIN`; chỉ một phía mạnh → `LIKELY`; nhắc tên, repost, tự nhận suông → `UNCONFIRMED`.
- **wallet:** công bố ví từ kênh chính thức (từ hai lần trở lên, hoặc hồ sơ launchpad) → `VERIFIED_OFFCHAIN`; một lần → `LIKELY`. **Không bao giờ** suy ra danh tính từ quan hệ ví.

## Cách viết trong memo

```
Project X:        @proj        VERIFIED_OFFCHAIN
Potential creator: @creatorA   LIKELY
Evidence:
- project_names_creator: https://x.com/proj/status/...
- (chưa có) creator tự nhận kèm địa chỉ hợp đồng
Deployer on-chain: 0xdddd... (VERIFIED_ONCHAIN). Liên kết deployer ↔ @creatorA: UNCONFIRMED.
```

Tách riêng ba chuyện: tài khoản dự án là thật, creator là ai, và ví nào thuộc về creator. Một mức cao ở chuyện này không kéo mức của chuyện kia lên theo.
