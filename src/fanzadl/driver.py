import argparse

from fanzadl.functions import get_library, parse_ranges, request

CSV_HEADER = "content,part,url"

if __name__ == "__main__":
    print("""
    _____                    ____  _     
    |  ___|_ _ _ __  ______ _|  _ \\| |    
    | |_ / _` | '_ \\|_  / _` | | | | |    
    |  _| (_| | | | |/ / (_| | |_| | |___ 
    |_|  \\__,_|_| |_/___\\__,_|____/|_____|                         
    """)
    print("Credits: @PicoQubit on EMP")
    print("License: GPL-3.0")
    print()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--content-index",
        help="Automatically select the content to be downloaded by its content ID, or index in the library. Comma separated, supports ranges. Use '*' to download everything.",
        type=str,
    )
    parser.add_argument(
        "--csv", help="Output stream URLs as a CSV file.", action="store_true"
    )
    parser.add_argument("--output", help="Output stream URLs into a file.", type=str)
    parser.add_argument(
        "--vr-quality",
        help="Target quality for VR streams. 'highest' or 'lowest' also supported.",
        type=str,
        default="highest",
        choices=["highest", "lowest", "8k", "uhq", "hq", "12000", "6000", "4000"],
    )
    args = parser.parse_args()

    choices = (
        args.content_index
        if args.content_index is not None
        else input(
            "Comma separated list of indices to download, supports ranges (e.g. '1,3-5,7'): "
        )
    )

    # region URL retrieval
    if args.output:
        with open(args.output, "w") as f:
            f.write((CSV_HEADER + "\n") if args.csv else "")
    if args.csv:
        print(CSV_HEADER)

    library = get_library()

    for choice in parse_ranges(choices, mappings):
        item = library[choice - 1]

        item_detail = request(
            "Digital_Api_Mylibrary.getDetail",
            {
                "mylibrary_id": item.get("mylibrary_id"),
                "product_id": item.get("product_id"),
                "shop_name": item.get("shop_name"),
            },
        )

        is_vr = item_detail.get("content_type") == "vr"

        if is_vr:
            pattern_data = item_detail.get("vr_rate_pattern").get("oculusquest2_vr")
            subpattern_data = pattern_data.get("stream")
            if args.vr_quality == "highest":
                bitrate_data = subpattern_data[-1]
            elif args.vr_quality == "lowest":
                bitrate_data = subpattern_data[0]
            else:
                bitrate_data = next(
                    filter(
                        lambda x: str(x.get("quality")) == args.vr_quality,
                        subpattern_data,
                    )
                )
        else:
            pattern_data = item_detail.get("rate_pattern").get("pc_pattern")
            subpattern_data = first_value(pattern_data).get("st")
            bitrate_data = subpattern_data.get("bitrate").get("0")

        part_count = bitrate_data.get("part")

        for part in range(part_count):
            """
            url_data = request("Digital_Api_Proxy.getURLPast", {
                "android_drm": False,
                "bitrate": "0",
                "drm": False,
                "chrome_cast": False,
                "isTablet": False,
                "licenseUID": license_uid,
                "product_id": product_id,
                "parent_product_id": item.get("product_id"),
                "transfer_type": "stream",
                "smartphone_access": False,
                "shop": item.get("shop_name"),
                "service": "digital",
                "part": str(part + 1),
            })
            url = url_data.get('redirect')
            """

            url_data = request_video(
                is_vr,
                item.get("mylibrary_id"),
                part + 1,
                bitrate_data.get("quality_group"),
            )
            url = url_data.get("content_info").get("redirect")
            final_url = f"{url}&{url_data.get('cookie_info').get('name')}={urllib.parse.quote(str(url_data.get('cookie_info').get('value')))}&smartphone_access=1"

            formatted_entry = final_url
            if args.csv:
                formatted_entry = f"{item.get('content_id')},{part + 1},{final_url}"

            print(formatted_entry)
            if args.output:
                with open(args.output, "a") as f:
                    f.write(formatted_entry + "\n")
