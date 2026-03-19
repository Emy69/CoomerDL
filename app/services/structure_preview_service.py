class StructurePreviewService:
    def build_preview_payload(self, settings: dict):
        folder_structure = settings.get("folder_structure", "default")
        file_naming_mode = settings.get("file_naming_mode", 0)

        file_name = self.get_example_file_name(file_naming_mode)

        if folder_structure == "flatten":
            return {
                "root": "Downloads",
                "folders": [],
                "files": [file_name],
            }

        if folder_structure == "by_service":
            return {
                "root": "Downloads",
                "folders": [
                    {
                        "name": "service_name",
                        "folders": [
                            {
                                "name": "creator_name",
                                "folders": [],
                                "files": [file_name],
                            }
                        ],
                        "files": [],
                    }
                ],
                "files": [],
            }

        if folder_structure == "by_user":
            return {
                "root": "Downloads",
                "folders": [
                    {
                        "name": "creator_name",
                        "folders": [],
                        "files": [file_name],
                    }
                ],
                "files": [],
            }

        # default
        return {
            "root": "Downloads",
            "folders": [
                {
                    "name": "service_name",
                    "folders": [
                        {
                            "name": "creator_name",
                            "folders": [
                                {
                                    "name": "post_id_or_title",
                                    "folders": [],
                                    "files": [file_name],
                                }
                            ],
                            "files": [],
                        }
                    ],
                    "files": [],
                }
            ],
            "files": [],
        }

    def get_example_file_name(self, file_naming_mode):
        mapping = {
            0: "123456789.jpg",
            1: "my_sample_post.jpg",
            2: "my_sample_post_12345.jpg",
            3: "2026-03-18_my_sample_post.jpg",
        }
        return mapping.get(file_naming_mode, "123456789.jpg")